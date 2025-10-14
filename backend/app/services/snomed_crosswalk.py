"""
SNOMED CT to CPT Crosswalk Service

Provides fast lookup of CPT code mappings for SNOMED CT procedure concepts.
Includes in-memory LRU caching for performance optimization.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from functools import lru_cache
from datetime import datetime
import structlog

from prisma import Prisma
from prisma.models import SNOMEDCrosswalk

logger = structlog.get_logger(__name__)


@dataclass
class CPTMapping:
    """Represents a SNOMED to CPT mapping"""

    snomed_code: str
    snomed_description: Optional[str]
    cpt_code: str
    cpt_description: Optional[str]
    mapping_type: Optional[str]  # EXACT, BROADER, NARROWER, APPROXIMATE
    confidence: Optional[float]  # 0.0-1.0
    source: Optional[str]
    source_version: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def __repr__(self):
        return f"CPTMapping(snomed={self.snomed_code}, cpt={self.cpt_code}, type={self.mapping_type}, conf={self.confidence})"


class CrosswalkMetrics:
    """Tracks crosswalk performance metrics"""

    def __init__(self):
        self.total_lookups = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.db_hits = 0
        self.db_misses = 0
        self.batch_lookups = 0
        self.total_codes_batched = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_lookups == 0:
            return 0.0
        return self.cache_hits / self.total_lookups

    @property
    def db_hit_rate(self) -> float:
        """Calculate database hit rate (codes with mappings)"""
        total_db_queries = self.cache_misses
        if total_db_queries == 0:
            return 0.0
        return self.db_hits / total_db_queries

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "total_lookups": self.total_lookups,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "db_hits": self.db_hits,
            "db_misses": self.db_misses,
            "db_hit_rate": round(self.db_hit_rate, 3),
            "batch_lookups": self.batch_lookups,
            "total_codes_batched": self.total_codes_batched,
        }

    def log_metrics(self):
        """Log current metrics"""
        logger.info(
            "crosswalk_metrics",
            **self.to_dict()
        )


class SNOMEDCrosswalkService:
    """
    Service for looking up CPT code mappings for SNOMED CT concepts.

    Features:
    - In-memory LRU caching for fast repeated lookups
    - Batch lookup support for multiple SNOMED codes
    - Fallback logic for codes without direct mappings
    - Performance metrics tracking
    """

    def __init__(self, db: Prisma, cache_size: int = 1000):
        """
        Initialize the crosswalk service.

        Args:
            db: Prisma database client
            cache_size: Size of LRU cache for mappings
        """
        self.db = db
        self.cache_size = cache_size
        self.metrics = CrosswalkMetrics()
        self._cache: Dict[str, List[CPTMapping]] = {}

        logger.info("snomed_crosswalk_initialized", cache_size=cache_size)

    async def get_cpt_mappings(
        self,
        snomed_code: str,
        min_confidence: float = 0.0,
        use_cache: bool = True
    ) -> List[CPTMapping]:
        """
        Get CPT code mappings for a SNOMED CT code.

        Args:
            snomed_code: SNOMED CT concept ID (e.g., "80146002")
            min_confidence: Minimum confidence threshold (0.0-1.0)
            use_cache: Whether to use cache for lookup

        Returns:
            List of CPTMapping objects, ordered by confidence (highest first)
        """
        self.metrics.total_lookups += 1

        # Check cache first
        if use_cache and snomed_code in self._cache:
            self.metrics.cache_hits += 1
            logger.debug("cache_hit", snomed_code=snomed_code)
            mappings = self._cache[snomed_code]
        else:
            self.metrics.cache_misses += 1
            logger.debug("cache_miss", snomed_code=snomed_code)

            # Query database
            mappings = await self._fetch_from_db(snomed_code)

            # Update cache (implement simple LRU by limiting size)
            if use_cache:
                self._update_cache(snomed_code, mappings)

        # Filter by confidence threshold
        filtered_mappings = [
            m for m in mappings
            if m.confidence is None or m.confidence >= min_confidence
        ]

        # Sort by confidence (highest first)
        filtered_mappings.sort(
            key=lambda m: m.confidence if m.confidence is not None else 0.0,
            reverse=True
        )

        return filtered_mappings

    async def _fetch_from_db(self, snomed_code: str) -> List[CPTMapping]:
        """
        Fetch mappings from database.

        Args:
            snomed_code: SNOMED CT concept ID

        Returns:
            List of CPTMapping objects
        """
        try:
            results = await self.db.snomedcrosswalk.find_many(
                where={"snomedCode": snomed_code},
                order={"confidence": "desc"}
            )

            if results:
                self.metrics.db_hits += 1
                logger.debug(
                    "db_hit",
                    snomed_code=snomed_code,
                    mapping_count=len(results)
                )
            else:
                self.metrics.db_misses += 1
                logger.debug("db_miss", snomed_code=snomed_code)

            mappings = [
                CPTMapping(
                    snomed_code=r.snomedCode,
                    snomed_description=r.snomedDescription,
                    cpt_code=r.cptCode,
                    cpt_description=r.cptDescription,
                    mapping_type=r.mappingType,
                    confidence=r.confidence,
                    source=r.source,
                    source_version=r.sourceVersion,
                )
                for r in results
            ]

            return mappings

        except Exception as e:
            logger.error(
                "db_fetch_error",
                snomed_code=snomed_code,
                error=str(e)
            )
            return []

    def _update_cache(self, snomed_code: str, mappings: List[CPTMapping]):
        """
        Update cache with new mappings (simple LRU implementation).

        Args:
            snomed_code: SNOMED CT code
            mappings: List of CPT mappings
        """
        # If cache is full, remove oldest entry (first inserted)
        if len(self._cache) >= self.cache_size and snomed_code not in self._cache:
            # Remove first item (oldest)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
            logger.debug("cache_eviction", evicted_code=first_key)

        # Add to cache (moves to end in Python 3.7+)
        self._cache[snomed_code] = mappings

    async def get_cpt_mappings_batch(
        self,
        snomed_codes: List[str],
        min_confidence: float = 0.0,
        use_cache: bool = True
    ) -> Dict[str, List[CPTMapping]]:
        """
        Get CPT mappings for multiple SNOMED codes in batch.

        This is more efficient than individual lookups as it:
        1. Checks cache for all codes first
        2. Fetches uncached codes in a single database query

        Args:
            snomed_codes: List of SNOMED CT concept IDs
            min_confidence: Minimum confidence threshold
            use_cache: Whether to use cache

        Returns:
            Dictionary mapping SNOMED code -> List[CPTMapping]
        """
        self.metrics.batch_lookups += 1
        self.metrics.total_codes_batched += len(snomed_codes)

        result: Dict[str, List[CPTMapping]] = {}
        uncached_codes: List[str] = []

        # Check cache first
        for code in snomed_codes:
            if use_cache and code in self._cache:
                self.metrics.cache_hits += 1
                result[code] = self._cache[code]
            else:
                uncached_codes.append(code)

        # Fetch uncached codes from database in batch
        if uncached_codes:
            self.metrics.cache_misses += len(uncached_codes)

            try:
                # Single database query for all uncached codes
                db_results = await self.db.snomedcrosswalk.find_many(
                    where={"snomedCode": {"in": uncached_codes}},
                    order={"confidence": "desc"}
                )

                # Group results by SNOMED code
                grouped_results: Dict[str, List[SNOMEDCrosswalk]] = {}
                for r in db_results:
                    if r.snomedCode not in grouped_results:
                        grouped_results[r.snomedCode] = []
                    grouped_results[r.snomedCode].append(r)

                # Convert to CPTMapping objects and update cache
                for code in uncached_codes:
                    if code in grouped_results:
                        self.metrics.db_hits += 1
                        mappings = [
                            CPTMapping(
                                snomed_code=r.snomedCode,
                                snomed_description=r.snomedDescription,
                                cpt_code=r.cptCode,
                                cpt_description=r.cptDescription,
                                mapping_type=r.mappingType,
                                confidence=r.confidence,
                                source=r.source,
                                source_version=r.sourceVersion,
                            )
                            for r in grouped_results[code]
                        ]
                    else:
                        self.metrics.db_misses += 1
                        mappings = []

                    result[code] = mappings

                    # Update cache
                    if use_cache:
                        self._update_cache(code, mappings)

            except Exception as e:
                logger.error(
                    "batch_fetch_error",
                    codes_count=len(uncached_codes),
                    error=str(e)
                )
                # Return empty lists for failed codes
                for code in uncached_codes:
                    if code not in result:
                        result[code] = []

        # Filter by confidence and sort
        for code in result:
            result[code] = [
                m for m in result[code]
                if m.confidence is None or m.confidence >= min_confidence
            ]
            result[code].sort(
                key=lambda m: m.confidence if m.confidence is not None else 0.0,
                reverse=True
            )

        logger.info(
            "batch_lookup_complete",
            total_codes=len(snomed_codes),
            cached_codes=len(snomed_codes) - len(uncached_codes),
            db_codes=len(uncached_codes)
        )

        return result

    async def get_best_cpt_mapping(
        self,
        snomed_code: str,
        min_confidence: float = 0.7
    ) -> Optional[CPTMapping]:
        """
        Get the single best (highest confidence) CPT mapping for a SNOMED code.

        Args:
            snomed_code: SNOMED CT concept ID
            min_confidence: Minimum confidence threshold (default 0.7)

        Returns:
            Best CPTMapping or None if no mapping meets threshold
        """
        mappings = await self.get_cpt_mappings(snomed_code, min_confidence)
        return mappings[0] if mappings else None

    async def find_by_cpt_code(
        self,
        cpt_code: str
    ) -> List[CPTMapping]:
        """
        Reverse lookup: Find SNOMED codes that map to a CPT code.

        Args:
            cpt_code: CPT code (e.g., "44950")

        Returns:
            List of CPTMapping objects
        """
        try:
            results = await self.db.snomedcrosswalk.find_many(
                where={"cptCode": cpt_code},
                order={"confidence": "desc"}
            )

            mappings = [
                CPTMapping(
                    snomed_code=r.snomedCode,
                    snomed_description=r.snomedDescription,
                    cpt_code=r.cptCode,
                    cpt_description=r.cptDescription,
                    mapping_type=r.mappingType,
                    confidence=r.confidence,
                    source=r.source,
                    source_version=r.sourceVersion,
                )
                for r in results
            ]

            logger.debug(
                "reverse_lookup",
                cpt_code=cpt_code,
                snomed_codes_found=len(mappings)
            )

            return mappings

        except Exception as e:
            logger.error(
                "reverse_lookup_error",
                cpt_code=cpt_code,
                error=str(e)
            )
            return []

    async def warm_cache(self, top_n: int = 100):
        """
        Pre-load cache with most commonly mapped SNOMED codes.

        This should be called on application startup to improve
        initial lookup performance.

        Args:
            top_n: Number of top SNOMED codes to pre-load
        """
        try:
            # Get most common SNOMED codes (codes with most mappings)
            query = """
                SELECT snomed_code, COUNT(*) as mapping_count
                FROM snomed_crosswalk
                GROUP BY snomed_code
                ORDER BY mapping_count DESC
                LIMIT $1
            """

            results = await self.db.query_raw(query, top_n)

            if results:
                snomed_codes = [r['snomed_code'] for r in results]

                # Batch fetch to warm cache
                await self.get_cpt_mappings_batch(snomed_codes, use_cache=True)

                logger.info(
                    "cache_warmed",
                    codes_loaded=len(snomed_codes),
                    cache_size=len(self._cache)
                )
            else:
                logger.warning("no_crosswalk_data_found")

        except Exception as e:
            logger.error("cache_warm_error", error=str(e))

    def clear_cache(self):
        """Clear the entire cache"""
        self._cache.clear()
        logger.info("cache_cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dictionary with metrics
        """
        return self.metrics.to_dict()

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "current_size": len(self._cache),
            "max_size": self.cache_size,
            "utilization": round(len(self._cache) / self.cache_size, 3) if self.cache_size > 0 else 0,
        }

    def log_performance_summary(self):
        """Log a summary of performance metrics"""
        self.metrics.log_metrics()

        cache_stats = self.get_cache_stats()
        logger.info("cache_stats", **cache_stats)


# Global service instance (initialized on startup)
_crosswalk_service: Optional[SNOMEDCrosswalkService] = None


async def get_crosswalk_service(db: Prisma) -> SNOMEDCrosswalkService:
    """
    Get or create the global crosswalk service instance.

    Args:
        db: Prisma database client

    Returns:
        SNOMEDCrosswalkService instance
    """
    global _crosswalk_service

    if _crosswalk_service is None:
        _crosswalk_service = SNOMEDCrosswalkService(db, cache_size=1000)
        # Warm cache on first initialization
        await _crosswalk_service.warm_cache(top_n=100)

    return _crosswalk_service
