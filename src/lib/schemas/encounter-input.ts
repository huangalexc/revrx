import { z } from 'zod'

const MAX_TEXT_LENGTH = 50_000 // 50,000 characters
const MAX_FILE_SIZE = 5_000_000 // 5MB
const ACCEPTED_FILE_TYPES = [
  'text/plain',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

// Text input schema
const textInputSchema = z.object({
  inputMethod: z.literal('text'),
  textContent: z
    .string()
    .min(50, 'Clinical note must be at least 50 characters')
    .max(
      MAX_TEXT_LENGTH,
      `Text must be less than ${MAX_TEXT_LENGTH.toLocaleString()} characters`
    ),
  file: z.any().optional(),
})

// File input schema
const fileInputSchema = z.object({
  inputMethod: z.literal('file'),
  textContent: z.string().optional(),
  file: z
    .any()
    .refine((files) => files?.length === 1, 'File is required')
    .refine(
      (files) => files?.[0]?.size <= MAX_FILE_SIZE,
      `File must be less than ${MAX_FILE_SIZE / 1_000_000}MB`
    )
    .refine(
      (files) => ACCEPTED_FILE_TYPES.includes(files?.[0]?.type),
      'Only TXT, PDF, and DOCX files are accepted'
    ),
})

// Discriminated union for either/or validation
export const encounterInputSchema = z.discriminatedUnion('inputMethod', [
  textInputSchema,
  fileInputSchema,
])

export type EncounterInputFormData = z.infer<typeof encounterInputSchema>

// Export constants for use in components
export { MAX_TEXT_LENGTH, MAX_FILE_SIZE, ACCEPTED_FILE_TYPES }
