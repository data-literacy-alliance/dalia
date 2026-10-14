import { z } from 'zod';

export const SuggestionLicenseSchema = z.object({
  value: z.string(),
  licenseId: z.string(),
  licenseName: z.string(),
  licenseLink: z.string(),
  licenseDescription: z.string(),
})
export type SuggestionLicense = z.infer<typeof SuggestionLicenseSchema>;
