import { z } from "zod";

export const neonFormFieldPropsSchema = z.object({
  label: z.string().min(1, "Label is required"),
  name: z.string().min(1, "Name is required"),
  error: z.string().optional(),
  hint: z.string().optional(),
  required: z.boolean().default(false),
});

export type NeonFormFieldProps = z.infer<typeof neonFormFieldPropsSchema>;
