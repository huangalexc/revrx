"""
Unit tests for SNOMED CT to CPT Crosswalk Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.snomed_crosswalk import (
    SNOMEDCrosswalkService,
    CPTMapping,
    CrosswalkMetrics,
    get_crosswalk_service,
)


@pytest.fixture
def mock_db():
    """Create a mock Prisma database client"""
    db = Mock()
    db.snomedcrosswalk = Mock()
    return db


@pytest.fixture
def crosswalk_service(mock_db):
    """Create a SNOMEDCrosswalkService instance with mock DB"""
    return SNOMEDCrosswalkService(db=mock_db, cache_size=10)


@pytest.fixture
def sample_db_result():
    """Sample database result"""
    result = Mock()
    result.snomedCode = "80146002"
    result.snomedDescription = "Appendectomy"
    result.cptCode = "44950"
    result.cptDescription = "Appendectomy"
    result.mappingType = "EXACT"
    result.confidence = 0.95
    result.source = "SAMPLE"
    result.sourceVersion = "2025"
    return result


class TestCPTMapping:
    """Test CPTMapping dataclass"""

    def test_create_mapping(self):
        """Test creating a CPT mapping"""
        mapping = CPTMapping(
            snomed_code="80146002",
            snomed_description="Appendectomy",
            cpt_code="44950",
            cpt_description="Appendectomy",
            mapping_type="EXACT",
            confidence=0.95,
            source="TEST",
            source_version="2025"
        )

        assert mapping.snomed_code == "80146002"
        assert mapping.cpt_code == "44950"
        assert mapping.confidence == 0.95

    def test_to_dict(self):
        """Test converting mapping to dictionary"""
        mapping = CPTMapping(
            snomed_code="80146002",
            snomed_description="Appendectomy",
            cpt_code="44950",
            cpt_description="Appendectomy",
            mapping_type="EXACT",
            confidence=0.95,
            source="TEST",
            source_version="2025"
        )

        result = mapping.to_dict()
        assert isinstance(result, dict)
        assert result["snomed_code"] == "80146002"
        assert result["cpt_code"] == "44950"


class TestCrosswalkMetrics:
    """Test CrosswalkMetrics class"""

    def test_initial_metrics(self):
        """Test initial metric values"""
        metrics = CrosswalkMetrics()

        assert metrics.total_lookups == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.cache_hit_rate == 0.0

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        metrics = CrosswalkMetrics()
        metrics.total_lookups = 100
        metrics.cache_hits = 75
        metrics.cache_misses = 25

        assert metrics.cache_hit_rate == 0.75

    def test_db_hit_rate_calculation(self):
        """Test database hit rate calculation"""
        metrics = CrosswalkMetrics()
        metrics.cache_misses = 50  # Total DB queries
        metrics.db_hits = 40  # Codes found in DB
        metrics.db_misses = 10  # Codes not found in DB

        assert metrics.db_hit_rate == 0.8

    def test_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = CrosswalkMetrics()
        metrics.total_lookups = 100
        metrics.cache_hits = 75

        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert "total_lookups" in result
        assert "cache_hit_rate" in result


class TestSNOMEDCrosswalkService:
    """Test SNOMEDCrosswalkService class"""

    @pytest.mark.asyncio
    async def test_get_cpt_mappings_cache_hit(self, crosswalk_service):
        """Test getting CPT mappings with cache hit"""
        # Pre-populate cache
        cached_mapping = CPTMapping(
            snomed_code="80146002",
            snomed_description="Appendectomy",
            cpt_code="44950",
            cpt_description="Appendectomy",
            mapping_type="EXACT",
            confidence=0.95,
            source="TEST",
            source_version="2025"
        )
        crosswalk_service._cache["80146002"] = [cached_mapping]

        # Get mappings (should hit cache)
        result = await crosswalk_service.get_cpt_mappings("80146002")

        assert len(result) == 1
        assert result[0].cpt_code == "44950"
        assert crosswalk_service.metrics.cache_hits == 1
        assert crosswalk_service.metrics.total_lookups == 1

    @pytest.mark.asyncio
    async def test_get_cpt_mappings_cache_miss(self, crosswalk_service, sample_db_result):
        """Test getting CPT mappings with cache miss"""
        # Mock database response
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[sample_db_result]
        )

        # Get mappings (should miss cache, hit DB)
        result = await crosswalk_service.get_cpt_mappings("80146002")

        assert len(result) == 1
        assert result[0].cpt_code == "44950"
        assert crosswalk_service.metrics.cache_misses == 1
        assert crosswalk_service.metrics.db_hits == 1

        # Verify it was added to cache
        assert "80146002" in crosswalk_service._cache

    @pytest.mark.asyncio
    async def test_get_cpt_mappings_not_found(self, crosswalk_service):
        """Test getting CPT mappings for code with no mappings"""
        # Mock empty database response
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[]
        )

        result = await crosswalk_service.get_cpt_mappings("99999999")

        assert len(result) == 0
        assert crosswalk_service.metrics.db_misses == 1

    @pytest.mark.asyncio
    async def test_get_cpt_mappings_confidence_filter(self, crosswalk_service):
        """Test filtering mappings by confidence threshold"""
        # Create mappings with different confidence levels
        high_conf = Mock()
        high_conf.snomedCode = "80146002"
        high_conf.snomedDescription = "Appendectomy"
        high_conf.cptCode = "44950"
        high_conf.cptDescription = "Appendectomy"
        high_conf.mappingType = "EXACT"
        high_conf.confidence = 0.95
        high_conf.source = "TEST"
        high_conf.sourceVersion = "2025"

        low_conf = Mock()
        low_conf.snomedCode = "80146002"
        low_conf.snomedDescription = "Appendectomy"
        low_conf.cptCode = "44960"
        low_conf.cptDescription = "Appendectomy with complications"
        low_conf.mappingType = "BROADER"
        low_conf.confidence = 0.60
        low_conf.source = "TEST"
        low_conf.sourceVersion = "2025"

        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[high_conf, low_conf]
        )

        # Get mappings with min_confidence = 0.7
        result = await crosswalk_service.get_cpt_mappings(
            "80146002",
            min_confidence=0.7
        )

        # Should only return high confidence mapping
        assert len(result) == 1
        assert result[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_get_cpt_mappings_sorted_by_confidence(self, crosswalk_service):
        """Test that mappings are sorted by confidence"""
        # Create mappings with different confidence levels
        results = []
        for i, conf in enumerate([0.60, 0.95, 0.80]):
            r = Mock()
            r.snomedCode = "80146002"
            r.snomedDescription = "Test"
            r.cptCode = f"4495{i}"
            r.cptDescription = f"Test {i}"
            r.mappingType = "EXACT"
            r.confidence = conf
            r.source = "TEST"
            r.sourceVersion = "2025"
            results.append(r)

        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=results
        )

        result = await crosswalk_service.get_cpt_mappings("80146002")

        # Should be sorted by confidence (highest first)
        assert result[0].confidence == 0.95
        assert result[1].confidence == 0.80
        assert result[2].confidence == 0.60

    @pytest.mark.asyncio
    async def test_batch_lookup(self, crosswalk_service, sample_db_result):
        """Test batch lookup of multiple SNOMED codes"""
        # Mock database response
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[sample_db_result]
        )

        codes = ["80146002", "73761001", "99999999"]
        result = await crosswalk_service.get_cpt_mappings_batch(codes)

        assert isinstance(result, dict)
        assert "80146002" in result
        assert crosswalk_service.metrics.batch_lookups == 1
        assert crosswalk_service.metrics.total_codes_batched == 3

    @pytest.mark.asyncio
    async def test_batch_lookup_with_cache(self, crosswalk_service):
        """Test batch lookup uses cache for cached codes"""
        # Pre-populate cache for one code
        cached_mapping = CPTMapping(
            snomed_code="80146002",
            snomed_description="Appendectomy",
            cpt_code="44950",
            cpt_description="Appendectomy",
            mapping_type="EXACT",
            confidence=0.95,
            source="TEST",
            source_version="2025"
        )
        crosswalk_service._cache["80146002"] = [cached_mapping]

        # Mock DB for uncached codes
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[]
        )

        codes = ["80146002", "73761001"]
        result = await crosswalk_service.get_cpt_mappings_batch(codes)

        # First code should come from cache
        assert "80146002" in result
        assert len(result["80146002"]) == 1
        assert crosswalk_service.metrics.cache_hits == 1

        # Second code should query DB
        assert "73761001" in result
        assert crosswalk_service.metrics.cache_misses == 1

    @pytest.mark.asyncio
    async def test_get_best_cpt_mapping(self, crosswalk_service):
        """Test getting the best (highest confidence) mapping"""
        # Create multiple mappings
        results = []
        for i, conf in enumerate([0.60, 0.95, 0.80]):
            r = Mock()
            r.snomedCode = "80146002"
            r.snomedDescription = "Test"
            r.cptCode = f"4495{i}"
            r.cptDescription = f"Test {i}"
            r.mappingType = "EXACT"
            r.confidence = conf
            r.source = "TEST"
            r.sourceVersion = "2025"
            results.append(r)

        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=results
        )

        best = await crosswalk_service.get_best_cpt_mapping("80146002", min_confidence=0.7)

        assert best is not None
        assert best.confidence == 0.95

    @pytest.mark.asyncio
    async def test_get_best_cpt_mapping_none(self, crosswalk_service):
        """Test getting best mapping when none meet threshold"""
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[]
        )

        best = await crosswalk_service.get_best_cpt_mapping("99999999")

        assert best is None

    @pytest.mark.asyncio
    async def test_find_by_cpt_code(self, crosswalk_service, sample_db_result):
        """Test reverse lookup by CPT code"""
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[sample_db_result]
        )

        result = await crosswalk_service.find_by_cpt_code("44950")

        assert len(result) == 1
        assert result[0].snomed_code == "80146002"

    @pytest.mark.asyncio
    async def test_cache_eviction(self, crosswalk_service):
        """Test that cache evicts oldest entry when full"""
        crosswalk_service.cache_size = 3  # Set small cache size

        # Mock DB
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[]
        )

        # Add 4 codes (should evict first one)
        for i in range(4):
            await crosswalk_service.get_cpt_mappings(f"CODE{i}")

        # Cache should have max 3 items
        assert len(crosswalk_service._cache) == 3

        # First code should be evicted
        assert "CODE0" not in crosswalk_service._cache

        # Last 3 codes should be present
        assert "CODE1" in crosswalk_service._cache
        assert "CODE2" in crosswalk_service._cache
        assert "CODE3" in crosswalk_service._cache

    @pytest.mark.asyncio
    async def test_warm_cache(self, crosswalk_service):
        """Test cache warming on startup"""
        # Mock query_raw to return top SNOMED codes
        crosswalk_service.db.query_raw = AsyncMock(
            return_value=[
                {"snomed_code": "80146002", "mapping_count": 5},
                {"snomed_code": "73761001", "mapping_count": 3},
            ]
        )

        # Mock find_many for batch lookup
        crosswalk_service.db.snomedcrosswalk.find_many = AsyncMock(
            return_value=[]
        )

        await crosswalk_service.warm_cache(top_n=10)

        # Cache should be populated
        assert len(crosswalk_service._cache) == 2

    def test_clear_cache(self, crosswalk_service):
        """Test clearing the cache"""
        crosswalk_service._cache["test"] = []
        assert len(crosswalk_service._cache) == 1

        crosswalk_service.clear_cache()

        assert len(crosswalk_service._cache) == 0

    def test_get_metrics(self, crosswalk_service):
        """Test getting metrics"""
        crosswalk_service.metrics.total_lookups = 100
        crosswalk_service.metrics.cache_hits = 75

        metrics = crosswalk_service.get_metrics()

        assert metrics["total_lookups"] == 100
        assert metrics["cache_hits"] == 75
        assert "cache_hit_rate" in metrics

    def test_get_cache_stats(self, crosswalk_service):
        """Test getting cache statistics"""
        crosswalk_service._cache["test1"] = []
        crosswalk_service._cache["test2"] = []

        stats = crosswalk_service.get_cache_stats()

        assert stats["current_size"] == 2
        assert stats["max_size"] == 10
        assert stats["utilization"] == 0.2


class TestGetCrosswalkService:
    """Test the get_crosswalk_service factory function"""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, mock_db):
        """Test that get_crosswalk_service returns same instance"""
        # Mock the warm_cache method to avoid DB calls
        with patch.object(SNOMEDCrosswalkService, 'warm_cache', new_callable=AsyncMock):
            service1 = await get_crosswalk_service(mock_db)
            service2 = await get_crosswalk_service(mock_db)

            # Should return the same instance
            assert service1 is service2
