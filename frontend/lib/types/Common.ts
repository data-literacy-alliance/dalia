import { z } from 'zod';

export type Language = 'en' | 'de';

export type Pageable<T> = {
  count: number;
  offset: number;
  limit: number;
  results: T[];
};

export type SocialMediaField = {
  name: string;
  url: string;
};

export const LabelValuePairSchema = z
  .object({
    label: z.string(),
    value: z.string().min(1),
  })
  .superRefine((item, ctx) => {
    const hasError = item.value.trim().length === 0;
    if (hasError) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Value is invalid.',
        path: [], // root error
      });
    }
  });
export type LabelValuePair = z.infer<typeof LabelValuePairSchema>;

export type LabelValueChild = LabelValuePair & {
  children: LabelValueChild[];
};

export type Suggestion = LabelValuePair;
