import { z } from 'zod';

export const FeedbackSchema = z.object({
  name: z.string(),
  email: z.string().email('Not a valid email address').min(1),
  userInput: z.string().min(1),
  submittedAt: z.coerce.date(),
  formMode: z.literal('production'),
});
