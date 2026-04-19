# Zod Validation Library - Best Practices for React Applications

A comprehensive guide to using Zod for type-safe validation in React applications.

## Table of Contents

1. [Zod Schema Definition Patterns](#1-zod-schema-definition-patterns)
2. [Form Validation with Zod (React Hook Form Integration)](#2-form-validation-with-zod-react-hook-form-integration)
3. [API Response Validation](#3-api-response-validation)
4. [Type Inference from Schemas](#4-type-inference-from-schemas)
5. [Error Handling and Custom Error Messages](#5-error-handling-and-custom-error-messages)
6. [Complex Schema Patterns](#6-complex-schema-patterns-objects-arrays-unions)
7. [Transformations and Refinements](#7-transformations-and-refinements)
8. [Async Validation](#8-async-validation)
9. [Environment Variable Validation](#9-environment-variable-validation)
10. [Reusing Schemas Across Frontend/Backend](#10-reusing-schemas-across-frontendbackend)

---

## 1. Zod Schema Definition Patterns

### Basic Primitive Schemas

```typescript
import * as z from "zod";

// Primitives
const stringSchema = z.string();
const numberSchema = z.number();
const booleanSchema = z.boolean();
const dateSchema = z.date();
const bigintSchema = z.bigint();

// Literals
const literalSchema = z.literal("hello");
const statusSchema = z.literal(["active", "inactive", "pending"]);
```

### Coercion Patterns

Use coercion when accepting form data or URL parameters that come as strings:

```typescript
// Coerce strings to other types
const coerceNumber = z.coerce.number();
const coerceBoolean = z.coerce.boolean();
const coerceDate = z.coerce.date();
const coerceBigInt = z.coerce.bigint();

// Examples
coerceNumber.parse("42");        // => 42
coerceBoolean.parse("true");     // => true
coerceDate.parse("2024-01-15");  // => Date object
```

### String Validation Patterns

```typescript
const emailSchema = z.email();
const uuidSchema = z.uuid();
const urlSchema = z.url();
const httpUrlSchema = z.httpUrl();  // http/https only

// String with constraints
const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters")
  .max(100, "Password is too long")
  .regex(/[A-Z]/, "Must contain at least one uppercase letter")
  .regex(/[a-z]/, "Must contain at least one lowercase letter")
  .regex(/[0-9]/, "Must contain at least one number")
  .regex(/[^A-Za-z0-9]/, "Must contain at least one special character");

// String transforms
const trimmedString = z.string().trim();
const lowercaseString = z.string().toLowerCase();
const normalizedString = z.string().normalize();
```

### Number Validation Patterns

```typescript
const positiveInt = z.int().positive();
const percentage = z.number().min(0).max(100);
const rating = z.number().min(1).max(5).step(0.5);

// Integer variants
const int32Schema = z.int32();    // 32-bit integer
const int64Schema = z.int64();    // 64-bit integer (bigint)
```

### Nullable and Optional Patterns

```typescript
// Optional (undefined allowed)
const optionalString = z.string().optional();
const optionalNumber = z.number().optional();

// Nullable (null allowed)
const nullableString = z.string().nullable();

// Nullish (both undefined and null allowed)
const nullishString = z.string().nullish();

// With defaults
const stringWithDefault = z.string().default("");
const numberWithDefault = z.number().default(0);
```

### Object Schema Patterns

```typescript
// Standard object (unknown keys stripped)
const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.email(),
  age: z.number().optional(),
  role: z.enum(["admin", "user", "guest"]).default("user"),
  createdAt: z.date().default(() => new Date()),
});

// Strict object (unknown keys throw error)
const StrictUserSchema = z.strictObject({
  id: z.string(),
  name: z.string(),
});

// Loose object (unknown keys pass through)
const LooseUserSchema = z.looseObject({
  id: z.string(),
  name: z.string(),
});

// Object with catchall for unknown keys
const FlexibleSchema = z.object({
  name: z.string(),
}).catchall(z.string());  // All other keys must be strings
```

### Schema Composition with Extend

```typescript
const BaseSchema = z.object({
  id: z.string().uuid(),
  createdAt: z.date(),
});

// Extend with new fields
const UserSchema = BaseSchema.extend({
  name: z.string(),
  email: z.email(),
});

// Alternative: Use spread syntax (more performant)
const UserSchema = z.object({
  ...BaseSchema.shape,
  name: z.string(),
  email: z.email(),
});

// Safe extend (won't allow overwriting with incompatible types)
const ExtendedSchema = BaseSchema.safeExtend({
  id: z.string().uuid(),  // ✅ Same type
  name: z.number(),       // ❌ Error - can't change type
});
```

---

## 2. Form Validation with Zod (React Hook Form Integration)

### Basic Setup

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

// Define your schema
const loginSchema = z.object({
  email: z.email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  rememberMe: z.boolean().default(false),
});

type LoginFormData = z.infer<typeof loginSchema>;

// Component
function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    console.log(data);
    // Submit to API
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <input {...register("email")} type="email" placeholder="Email" />
        {errors.email && <span>{errors.email.message}</span>}
      </div>
      
      <div>
        <input {...register("password")} type="password" placeholder="Password" />
        {errors.password && <span>{errors.password.message}</span>}
      </div>
      
      <div>
        <label>
          <input {...register("rememberMe")} type="checkbox" />
          Remember me
        </label>
      </div>
      
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Logging in..." : "Login"}
      </button>
    </form>
  );
}
```

### Advanced Form Schema with Nested Objects

```typescript
const addressSchema = z.object({
  street: z.string().min(1, "Street is required"),
  city: z.string().min(1, "City is required"),
  zipCode: z.string().regex(/^\d{5}(-\d{4})?$/, "Invalid ZIP code"),
  country: z.string().min(1, "Country is required"),
});

const userRegistrationSchema = z.object({
  personalInfo: z.object({
    firstName: z.string().min(1, "First name is required"),
    lastName: z.string().min(1, "Last name is required"),
    dateOfBirth: z.coerce.date().optional(),
  }),
  contactInfo: z.object({
    email: z.email("Valid email required"),
    phone: z.string().regex(/^\+?[\d\s-()]+$/, "Invalid phone number").optional(),
  }),
  addresses: z.object({
    billing: addressSchema,
    shipping: addressSchema.optional(),
  }).refine(
    (data) => data.shipping || data.billing,
    { message: "At least one address is required", path: ["billing"] }
  ),
  preferences: z.object({
    newsletter: z.boolean().default(false),
    notifications: z.object({
      email: z.boolean().default(true),
      sms: z.boolean().default(false),
      push: z.boolean().default(true),
    }),
  }),
});

type UserRegistrationData = z.infer<typeof userRegistrationSchema>;
```

### Form with Array Fields

```typescript
const todoSchema = z.object({
  title: z.string().min(1, "Title is required"),
  completed: z.boolean().default(false),
});

const todoListSchema = z.object({
  listName: z.string().min(1, "List name is required"),
  todos: z.array(todoSchema).min(1, "Add at least one todo"),
});

import { useFieldArray } from "react-hook-form";

function TodoListForm() {
  const { register, control, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(todoListSchema),
    defaultValues: {
      listName: "",
      todos: [{ title: "", completed: false }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "todos",
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("listName")} placeholder="List Name" />
      {errors.listName && <span>{errors.listName.message}</span>}

      {fields.map((field, index) => (
        <div key={field.id}>
          <input
            {...register(`todos.${index}.title`)}
            placeholder="Todo title"
          />
          <input
            {...register(`todos.${index}.completed`)}
            type="checkbox"
          />
          <button type="button" onClick={() => remove(index)}>
            Remove
          </button>
          {errors.todos?.[index]?.title && (
            <span>{errors.todos[index].title.message}</span>
          )}
        </div>
      ))}

      <button
        type="button"
        onClick={() => append({ title: "", completed: false })}
      >
        Add Todo
      </button>

      <button type="submit">Save List</button>
    </form>
  );
}
```

### Password Confirmation Pattern

```typescript
const passwordSchema = z.object({
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain uppercase letter")
    .regex(/[a-z]/, "Must contain lowercase letter")
    .regex(/\d/, "Must contain number"),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"], // Error will be associated with confirmPassword field
});
```

---

## 3. API Response Validation

### Basic API Response Validation

```typescript
// Define response schemas
const userResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  email: z.email(),
  avatar: z.url().nullable(),
  createdAt: z.iso.datetime(),
});

const apiResponseSchema = z.object({
  success: z.boolean(),
  data: userResponseSchema,
  message: z.string().optional(),
});

// API function with validation
async function fetchUser(userId: string) {
  const response = await fetch(`/api/users/${userId}`);
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const json = await response.json();
  
  // Validate the response
  const result = apiResponseSchema.safeParse(json);
  
  if (!result.success) {
    console.error("Invalid API response:", result.error.issues);
    throw new Error("Invalid response from server");
  }
  
  return result.data;
}
```

### Handling Different Response Types

```typescript
// Success response
const successResponseSchema = z.object({
  success: z.literal(true),
  data: z.unknown(),  // Will be refined based on endpoint
});

// Error response
const errorResponseSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});

// Union of responses
const apiResponseSchema = z.union([successResponseSchema, errorResponseSchema]);

async function apiCall<T>(
  url: string,
  dataSchema: z.ZodSchema<T>
): Promise<T> {
  const response = await fetch(url);
  const json = await response.json();
  
  const result = apiResponseSchema.safeParse(json);
  
  if (!result.success) {
    throw new Error("Invalid API response format");
  }
  
  if (!result.data.success) {
    throw new Error(result.data.error.message);
  }
  
  // Parse the actual data with the provided schema
  const dataResult = dataSchema.safeParse(result.data.data);
  
  if (!dataResult.success) {
    throw new Error("Invalid data format from API");
  }
  
  return dataResult.data;
}

// Usage
const users = await apiCall(
  "/api/users",
  z.array(userResponseSchema)
);
```

### Paginated Response Pattern

```typescript
const paginationSchema = z.object({
  page: z.number().int().positive(),
  perPage: z.number().int().positive(),
  total: z.number().int().nonnegative(),
  totalPages: z.number().int().nonnegative(),
});

function createPaginatedSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    pagination: paginationSchema,
  });
}

// Usage
const userListSchema = createPaginatedSchema(userResponseSchema);
type UserListResponse = z.infer<typeof userListSchema>;
```

### API Client with Built-in Validation

```typescript
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async get<T>(path: string, schema: z.ZodSchema<T>): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`);
    
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    const data = await response.json();
    return this.validate(schema, data);
  }

  async post<T>(
    path: string,
    body: unknown,
    responseSchema: z.ZodSchema<T>
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return this.validate(responseSchema, data);
  }

  private validate<T>(schema: z.ZodSchema<T>, data: unknown): T {
    const result = schema.safeParse(data);
    
    if (!result.success) {
      console.error("Validation failed:", result.error.issues);
      throw new ValidationError(result.error);
    }
    
    return result.data;
  }
}

// Usage
const api = new ApiClient("https://api.example.com");

const user = await api.get("/users/123", userResponseSchema);
```

---

## 4. Type Inference from Schemas

### Basic Type Inference

```typescript
import * as z from "zod";

const userSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  email: z.email(),
  age: z.number().optional(),
});

// Extract the TypeScript type
type User = z.infer<typeof userSchema>;

// User is equivalent to:
// type User = {
//   id: string;
//   name: string;
//   email: string;
//   age?: number | undefined;
// }
```

### Input vs Output Types

When using transforms, input and output types can differ:

```typescript
const transformedSchema = z
  .string()
  .transform((val) => val.toUpperCase())
  .transform((val) => val.length);

// Input type (before transforms)
type InputType = z.input<typeof transformedSchema>;
// => string

// Output type (after transforms) - same as z.infer
type OutputType = z.output<typeof transformedSchema>;
// => number
```

### Creating Reusable Type Utilities

```typescript
// Extract nullable type
type Nullable<T> = z.infer<ReturnType<typeof z.nullable<z.ZodType<T>>>>;

// Extract array item type
type ArrayElement<T> = T extends z.ZodArray<infer U> 
  ? z.infer<U> 
  : never;

// Extract object keys as union
type ObjectKeys<T extends z.ZodObject<any>> = keyof z.infer<T>;

// Usage
const usersSchema = z.array(userSchema);
type UserArrayElement = ArrayElement<typeof usersSchema>;
// => User
```

### Schema to Type Patterns

```typescript
// Create types for different use cases
const createUserSchema = z.object({
  name: z.string(),
  email: z.email(),
  password: z.string().min(8),
});

const updateUserSchema = createUserSchema.partial().extend({
  id: z.string().uuid(),
});

// Extract types
type CreateUserInput = z.infer<typeof createUserSchema>;
type UpdateUserInput = z.infer<typeof updateUserSchema>;

// Create partial types for updates
type PartialUser = Partial<z.infer<typeof userSchema>>;

// Create required version of all fields
type RequiredUser = Required<z.infer<typeof userSchema>>;
```

### Utility Types for Form Handling

```typescript
// Make all fields nullable (useful for reset values)
type Nullable<T> = { [K in keyof T]: T[K] | null };

// Form field types
type FormFieldState = {
  value: string;
  error?: string;
  touched: boolean;
};

type FormState<T> = {
  [K in keyof T]: FormFieldState;
};

// Create form state from schema
type UserFormState = FormState<z.infer<typeof userSchema>>;
```

---

## 5. Error Handling and Custom Error Messages

### Schema-Level Error Messages

```typescript
const userSchema = z.object({
  email: z.email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters long")
    .max(100, "Password is too long"),
  age: z.number().min(0, "Age cannot be negative").max(150, "Age is unrealistic"),
});
```

### Dynamic Error Messages

```typescript
const dynamicErrorSchema = z.object({
  username: z.string().min(3, {
    error: (issue) => {
      const currentLength = String(issue.input).length;
      return `Username must be at least 3 characters. You entered ${currentLength}.`;
    },
  }),
  password: z.string().refine((val) => val.length >= 8, {
    error: (issue) => {
      if (typeof issue.input === "string") {
        return `Password is ${issue.input.length} characters. Minimum is 8.`;
      }
      return "Password is required";
    },
  }),
});
```

### Per-Parse Error Customization

```typescript
const schema = z.string();

// Customize error for a specific parse operation
schema.parse(123, {
  error: (issue) => "This field must be a string",
});

// With safeParse
const result = schema.safeParse(123, {
  error: (issue) => {
    if (issue.code === "invalid_type") {
      return `Expected ${issue.expected}, but received ${issue.received}`;
    }
    return "Validation failed";
  },
});
```

### Global Error Configuration

```typescript
import * as z from "zod";

// Configure global error handling
z.config({
  customError: (issue) => {
    switch (issue.code) {
      case "invalid_type":
        return `Expected ${issue.expected} but got ${issue.received}`;
      case "too_small":
        return `Value must be at least ${issue.minimum}`;
      case "too_big":
        return `Value must be at most ${issue.maximum}`;
      default:
        return undefined; // Use default message
    }
  },
});
```

### Error Formatting Utilities

```typescript
// Format errors for display
function formatZodError(error: z.ZodError): Record<string, string> {
  const formatted: Record<string, string> = {};
  
  for (const issue of error.issues) {
    const path = issue.path.join(".");
    formatted[path] = issue.message;
  }
  
  return formatted;
}

// Format errors for React Hook Form
function formatErrorsForRHF(error: z.ZodError) {
  const errors: Record<string, { message: string; type: string }> = {};
  
  for (const issue of error.issues) {
    const path = issue.path.join(".");
    errors[path] = {
      message: issue.message,
      type: issue.code,
    };
  }
  
  return errors;
}

// Usage
const result = schema.safeParse(data);

if (!result.success) {
  const errors = formatZodError(result.error);
  // { "email": "Invalid email", "password": "Too short" }
}
```

### Field-Level Error Component

```typescript
interface FieldErrorProps {
  error?: z.ZodIssue;
}

function FieldError({ error }: FieldErrorProps) {
  if (!error) return null;
  
  return (
    <span className="error-message" role="alert">
      {error.message}
    </span>
  );
}

// Custom error summary
interface ErrorSummaryProps {
  errors: z.ZodIssue[];
}

function ErrorSummary({ errors }: ErrorSummaryProps) {
  if (errors.length === 0) return null;
  
  return (
    <div className="error-summary" role="alert">
      <h3>Please correct the following errors:</h3>
      <ul>
        {errors.map((error, index) => (
          <li key={index}>
            <strong>{error.path.join(".")}:</strong> {error.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

## 6. Complex Schema Patterns (Objects, Arrays, Unions)

### Nested Object Schemas

```typescript
const addressSchema = z.object({
  street: z.string(),
  city: z.string(),
  state: z.string().length(2),
  zipCode: z.string().regex(/^\d{5}(-\d{4})?$/),
  country: z.string().default("US"),
});

const companySchema = z.object({
  name: z.string(),
  address: addressSchema,
  billingAddress: addressSchema.optional(),
});

const employeeSchema = z.object({
  name: z.string(),
  company: companySchema,
  homeAddress: addressSchema,
});
```

### Array Validation Patterns

```typescript
// Basic array
const tagsSchema = z.array(z.string().min(1)).min(1).max(10);

// Array of objects
const todosSchema = z.array(
  z.object({
    id: z.string().uuid(),
    title: z.string().min(1),
    completed: z.boolean(),
    priority: z.enum(["low", "medium", "high"]),
  })
);

// Unique array values
const uniqueTagsSchema = z
  .array(z.string())
  .refine((items) => new Set(items).size === items.length, {
    message: "All tags must be unique",
  });

// Array with specific length
const exactlyThreeSchema = z.array(z.number()).length(3);

// Non-empty array
const nonEmptySchema = z.array(z.string()).min(1);
```

### Union and Discriminated Union Patterns

```typescript
// Simple union
const stringOrNumber = z.union([z.string(), z.number()]);

// Object unions (use discriminated unions for better performance)
const textMessageSchema = z.object({
  type: z.literal("text"),
  content: z.string(),
});

const imageMessageSchema = z.object({
  type: z.literal("image"),
  url: z.url(),
  caption: z.string().optional(),
});

const fileMessageSchema = z.object({
  type: z.literal("file"),
  name: z.string(),
  size: z.number(),
  mimeType: z.string(),
});

// Discriminated union - more efficient parsing
const messageSchema = z.discriminatedUnion("type", [
  textMessageSchema,
  imageMessageSchema,
  fileMessageSchema,
]);

type Message = z.infer<typeof messageSchema>;

// Usage with type narrowing
function processMessage(message: Message) {
  switch (message.type) {
    case "text":
      return message.content;  // TypeScript knows this is TextMessage
    case "image":
      return message.url;      // TypeScript knows this is ImageMessage
    case "file":
      return message.name;     // TypeScript knows this is FileMessage
  }
}
```

### Intersection Types

```typescript
const baseEntitySchema = z.object({
  id: z.string().uuid(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

const userAttributesSchema = z.object({
  name: z.string(),
  email: z.email(),
});

// Combine schemas
const userSchema = z.intersection(baseEntitySchema, userAttributesSchema);

// Alternative using extend (preferred for objects)
const userSchemaAlt = baseEntitySchema.extend(userAttributesSchema.shape);
```

### Tuple Patterns

```typescript
// Fixed-length tuple
const coordinateSchema = z.tuple([z.number(), z.number()]);
// => [number, number]

// Mixed types tuple
const userTupleSchema = z.tuple([
  z.string(),  // name
  z.number(),  // age
  z.boolean(), // isActive
]);

// Variadic tuple
const variadicTuple = z.tuple([z.string()], z.number());
// => [string, ...number[]]
```

### Record Patterns

```typescript
// Record with string keys and number values
const scoresSchema = z.record(z.string(), z.number());
// => Record<string, number>

// Record with enum keys (all keys required)
const rolePermissionsSchema = z.record(
  z.enum(["admin", "user", "guest"]),
  z.boolean()
);
// => { admin: boolean; user: boolean; guest: boolean }

// Partial record (keys optional)
const partialPermissionsSchema = z.partialRecord(
  z.enum(["read", "write", "delete"]),
  z.boolean()
);
// => { read?: boolean; write?: boolean; delete?: boolean }

// Loose record (allows non-matching keys)
const looseRecordSchema = z.looseRecord(z.string().regex(/^pref_/), z.string());
```

### Recursive Schemas

```typescript
// Recursive category schema
const categorySchema: z.ZodType<Category> = z.object({
  name: z.string(),
  subcategories: z.lazy(() => z.array(categorySchema).optional()),
});

interface Category {
  name: string;
  subcategories?: Category[];
}

// File tree structure
const fileNodeSchema: z.ZodType<FileNode> = z.object({
  name: z.string(),
  type: z.enum(["file", "directory"]),
  size: z.number().optional(),
  children: z.lazy(() => z.array(fileNodeSchema).optional()),
});

interface FileNode {
  name: string;
  type: "file" | "directory";
  size?: number;
  children?: FileNode[];
}
```

---

## 7. Transformations and Refinements

### Basic Transforms

```typescript
// String transformations
const trimmedUpperCase = z
  .string()
  .transform((val) => val.trim())
  .transform((val) => val.toUpperCase());

// Number transformations
const roundedNumber = z
  .number()
  .transform((val) => Math.round(val));

// Chain transforms with pipe
const stringToLength = z
  .string()
  .pipe(z.transform((val) => val.length));
// Input: string, Output: number
```

### Preprocessing

```typescript
// Coerce string to number before validation
const preprocessedNumber = z.preprocess(
  (val) => {
    if (typeof val === "string") {
      return parseFloat(val);
    }
    return val;
  },
  z.number()
);

// Preprocess to handle empty strings as undefined
const optionalString = z.preprocess(
  (val) => (val === "" ? undefined : val),
  z.string().optional()
);

// Preprocess arrays (handle single value or array)
const stringArray = z.preprocess(
  (val) => {
    if (Array.isArray(val)) return val;
    if (val === undefined || val === null) return [];
    return [val];
  },
  z.array(z.string())
);
```

### Refinements for Custom Validation

```typescript
// Basic refinement
const evenNumber = z.number().refine((n) => n % 2 === 0, {
  message: "Number must be even",
});

// Refinement with custom path (for objects)
const passwordSchema = z
  .object({
    password: z.string().min(8),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

// Multiple refinements
const strongPassword = z
  .string()
  .refine((val) => /[A-Z]/.test(val), {
    message: "Must contain uppercase letter",
  })
  .refine((val) => /[a-z]/.test(val), {
    message: "Must contain lowercase letter",
  })
  .refine((val) => /\d/.test(val), {
    message: "Must contain number",
  });
```

### Super Refine for Complex Validation

```typescript
import * as z from "zod";

const uniqueStringArray = z.array(z.string()).superRefine((val, ctx) => {
  const seen = new Set<string>();
  
  for (let i = 0; i < val.length; i++) {
    if (seen.has(val[i])) {
      ctx.addIssue({
        code: "custom",
        message: `Duplicate value: ${val[i]}`,
        path: [i],
      });
    }
    seen.add(val[i]);
  }
});

// Complex object validation
const bookingSchema = z
  .object({
    checkIn: z.date(),
    checkOut: z.date(),
    guests: z.number().positive(),
  })
  .superRefine((data, ctx) => {
    if (data.checkOut <= data.checkIn) {
      ctx.addIssue({
        code: "custom",
        message: "Check-out must be after check-in",
        path: ["checkOut"],
      });
    }
    
    const maxGuests = 10;
    if (data.guests > maxGuests) {
      ctx.addIssue({
        code: "too_big",
        message: `Maximum ${maxGuests} guests allowed`,
        maximum: maxGuests,
        inclusive: true,
        origin: "number",
        path: ["guests"],
      });
    }
  });
```

### Codecs for Bidirectional Transformations

```typescript
// Date codec (ISO string <-> Date)
const isoDateCodec = z.codec(
  z.iso.datetime(),
  z.date(),
  {
    decode: (isoString) => new Date(isoString),
    encode: (date) => date.toISOString(),
  }
);

// Number codec (string <-> number)
const stringNumberCodec = z.codec(
  z.string(),
  z.number(),
  {
    decode: (str) => parseFloat(str),
    encode: (num) => num.toString(),
  }
);

// URL codec
const urlCodec = z.codec(
  z.string(),
  z.instanceof(URL),
  {
    decode: (str) => new URL(str),
    encode: (url) => url.href,
  }
);

// Usage
const isoDate = isoDateCodec.parse("2024-01-15T10:30:00.000Z");
// => Date object

const encoded = z.encode(isoDateCodec, new Date());
// => ISO string
```

### Common Transform Patterns

```typescript
// Normalize email
const normalizedEmail = z
  .email()
  .transform((val) => val.toLowerCase().trim());

// Parse JSON string
const jsonString = z
  .string()
  .transform((str) => JSON.parse(str));

// CSV to array
const csvToArray = z
  .string()
  .transform((val) => val.split(",").map((s) => s.trim()));

// Phone number normalization
const phoneSchema = z
  .string()
  .transform((val) => val.replace(/\D/g, ""))
  .refine((val) => val.length === 10, {
    message: "Phone number must have 10 digits",
  });
```

---

## 8. Async Validation

### Basic Async Refinement

```typescript
// Check if username is available
const uniqueUsernameSchema = z
  .string()
  .min(3)
  .refine(
    async (username) => {
      const response = await fetch(`/api/check-username?username=${username}`);
      const data = await response.json();
      return data.available;
    },
    {
      message: "Username is already taken",
    }
  );

// Usage (must use parseAsync)
const isAvailable = await uniqueUsernameSchema.parseAsync("john_doe");
```

### Async Transform

```typescript
// Fetch user by ID and validate
const userByIdSchema = z
  .string().uuid()
  .transform(async (id) => {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error("User not found");
    return response.json();
  })
  .pipe(userSchema);

// Usage
const user = await userByIdSchema.parseAsync("550e8400-e29b-41d4-a716-446655440000");
```

### Form with Async Validation

```typescript
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const signupSchema = z.object({
  username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .refine(
      async (username) => {
        // Debounced check
        const response = await fetch(`/api/check-username?username=${username}`);
        const data = await response.json();
        return data.available;
      },
      { message: "Username is already taken" }
    ),
  email: z.email(),
  password: z.string().min(8),
});

function SignupForm() {
  const { register, handleSubmit, formState: { errors, isValidating } } = useForm({
    resolver: zodResolver(signupSchema),
    mode: "onBlur",
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <div>
        <input {...register("username")} placeholder="Username" />
        {isValidating && <span>Checking availability...</span>}
        {errors.username && <span>{errors.username.message}</span>}
      </div>
      {/* ... */}
    </form>
  );
}
```

### Custom Async Validation Hook

```typescript
function useAsyncValidation<T>(
  schema: z.ZodSchema<T>,
  debounceMs: number = 500
) {
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<z.ZodError | null>(null);

  const validate = useCallback(
    debounce(async (value: unknown) => {
      setIsValidating(true);
      setError(null);

      try {
        const result = await schema.parseAsync(value);
        return { success: true as const, data: result };
      } catch (err) {
        if (err instanceof z.ZodError) {
          setError(err);
          return { success: false as const, error: err };
        }
        throw err;
      } finally {
        setIsValidating(false);
      }
    }, debounceMs),
    [schema, debounceMs]
  );

  return { validate, isValidating, error };
}

// Usage
function UsernameField() {
  const [username, setUsername] = useState("");
  const { validate, isValidating, error } = useAsyncValidation(
    uniqueUsernameSchema,
    300
  );

  useEffect(() => {
    if (username) {
      validate(username);
    }
  }, [username, validate]);

  return (
    <div>
      <input
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
      />
      {isValidating && <span>Checking...</span>}
      {error && <span>{error.issues[0]?.message}</span>}
    </div>
  );
}
```

### API Response with Async Schema

```typescript
const paginatedSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    data: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    perPage: z.number(),
  });

async function fetchWithValidation<T>(
  url: string,
  schema: z.ZodSchema<T>
): Promise<T> {
  const response = await fetch(url);
  const json = await response.json();
  
  // Use safeParseAsync for async schemas
  const result = await schema.safeParseAsync(json);
  
  if (!result.success) {
    console.error("Validation failed:", result.error.issues);
    throw new Error("Invalid response from server");
  }
  
  return result.data;
}
```

---

## 9. Environment Variable Validation

### Basic Environment Validation

```typescript
// env.ts
import * as z from "zod";

const envSchema = z.object({
  // Required variables
  NODE_ENV: z.enum(["development", "production", "test"]),
  API_URL: z.url(),
  DATABASE_URL: z.string().min(1),
  
  // Optional with defaults
  PORT: z.coerce.number().default(3000),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  
  // Boolean from string (Zod 4+)
  ENABLE_ANALYTICS: z.stringbool().default(false),
  DEBUG_MODE: z.stringbool().default(false),
});

// Validate process.env
const parsedEnv = envSchema.safeParse(process.env);

if (!parsedEnv.success) {
  console.error(
    "❌ Invalid environment variables:",
    parsedEnv.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("\n")
  );
  process.exit(1);
}

export const env = parsedEnv.data;
```

### Split Client/Server Environment Variables

```typescript
// env.ts
import * as z from "zod";

// Client-side env (must be prefixed with NEXT_PUBLIC_ for Next.js)
const clientEnvSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url(),
  NEXT_PUBLIC_APP_NAME: z.string().default("My App"),
  NEXT_PUBLIC_STRIPE_PUBLIC_KEY: z.string().optional(),
});

// Server-side only env
const serverEnvSchema = z.object({
  DATABASE_URL: z.string().min(1),
  JWT_SECRET: z.string().min(32),
  STRIPE_SECRET_KEY: z.string().min(1),
  SENDGRID_API_KEY: z.string().optional(),
  REDIS_URL: z.string().optional(),
});

// Combined schema
const combinedSchema = clientEnvSchema.merge(serverEnvSchema);

// Type helpers
type ClientEnv = z.infer<typeof clientEnvSchema>;
type ServerEnv = z.infer<typeof serverEnvSchema>;
type CombinedEnv = z.infer<typeof combinedSchema>;

// Validate based on environment
function validateEnv() {
  const isServer = typeof window === "undefined";
  
  // On client, only validate client env
  const schema = isServer ? combinedSchema : clientEnvSchema;
  
  const result = schema.safeParse(process.env);
  
  if (!result.success) {
    const errors = result.error.issues.map(
      (i) => `${i.path.join(".")}: ${i.message}`
    );
    
    if (isServer) {
      console.error("❌ Invalid server environment variables:\n", errors.join("\n"));
      process.exit(1);
    } else {
      console.error("❌ Invalid client environment variables:\n", errors.join("\n"));
      throw new Error("Environment validation failed");
    }
  }
  
  return result.data;
}

export const env = validateEnv();
```

### Environment-Specific Validation

```typescript
// env.ts
import * as z from "zod";

const baseSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]),
  API_URL: z.url(),
});

const developmentSchema = baseSchema.extend({
  DEBUG: z.stringbool().default(true),
  MOCK_API: z.stringbool().default(false),
  HOT_RELOAD: z.stringbool().default(true),
});

const productionSchema = baseSchema.extend({
  DEBUG: z.stringbool().default(false),
  SENTRY_DSN: z.url(),
  CDN_URL: z.url(),
  ANALYTICS_ID: z.string(),
});

const testSchema = baseSchema.extend({
  TEST_DATABASE_URL: z.string(),
  MOCK_EXTERNAL_APIS: z.stringbool().default(true),
});

// Select schema based on environment
function getEnvSchema() {
  const nodeEnv = process.env.NODE_ENV;
  
  switch (nodeEnv) {
    case "production":
      return productionSchema;
    case "test":
      return testSchema;
    case "development":
    default:
      return developmentSchema;
  }
}

const envSchema = getEnvSchema();
const result = envSchema.safeParse(process.env);

if (!result.success) {
  console.error("Environment validation failed:", result.error.format());
  process.exit(1);
}

export const env = result.data;
```

### Environment Variable Utility Functions

```typescript
// utils/env.ts
import * as z from "zod";

/**
 * Parse a comma-separated list from env variable
 */
export function parseList<T extends z.ZodTypeAny>(
  schema: T,
  separator: string = ","
): z.ZodEffects<z.ZodString, z.infer<T>[], string> {
  return z.string().transform((val) =>
    val
      .split(separator)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((item) => schema.parse(item))
  );
}

/**
 * Parse JSON from env variable
 */
export function parseJson<T extends z.ZodTypeAny>(schema: T) {
  return z.string().transform((str) => {
    try {
      const parsed = JSON.parse(str);
      return schema.parse(parsed);
    } catch {
      throw new Error("Invalid JSON in environment variable");
    }
  });
}

/**
 * Parse number with units (e.g., "1mb", "5kb")
 */
export function parseByteSize() {
  return z.string().transform((val) => {
    const match = val.match(/^(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)?$/i);
    if (!match) throw new Error("Invalid byte size format");
    
    const num = parseFloat(match[1]);
    const unit = (match[2] || "b").toLowerCase();
    
    const multipliers: Record<string, number> = {
      b: 1,
      kb: 1024,
      mb: 1024 ** 2,
      gb: 1024 ** 3,
    };
    
    return Math.floor(num * multipliers[unit]);
  });
}

// Usage in schema
const envSchema = z.object({
  ALLOWED_ORIGINS: parseList(z.url()),
  FEATURE_FLAGS: parseJson(z.record(z.string(), z.boolean())),
  MAX_FILE_SIZE: parseByteSize().default("5mb"),
  RATE_LIMIT: z.coerce.number().default(100),
});
```

---

## 10. Reusing Schemas Across Frontend/Backend

### Shared Schema Package Structure

```
packages/
├── schemas/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── index.ts
│       ├── user.ts
│       ├── product.ts
│       ├── api.ts
│       └── utils.ts
├── frontend/
│   └── package.json
└── backend/
    └── package.json
```

### Shared Schema Definitions

```typescript
// packages/schemas/src/user.ts
import * as z from "zod";

// Base user schema
export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.email(),
  name: z.string().min(1),
  avatar: z.url().nullable(),
  createdAt: z.iso.datetime(),
  updatedAt: z.iso.datetime(),
});

export type User = z.infer<typeof userSchema>;

// Create user schema (for registration)
export const createUserSchema = z.object({
  email: z.email(),
  name: z.string().min(1),
  password: z
    .string()
    .min(8)
    .regex(/[A-Z]/, "Must contain uppercase")
    .regex(/[a-z]/, "Must contain lowercase")
    .regex(/\d/, "Must contain number"),
});

export type CreateUserInput = z.infer<typeof createUserSchema>;

// Update user schema (partial)
export const updateUserSchema = userSchema.partial().pick({
  name: true,
  avatar: true,
});

export type UpdateUserInput = z.infer<typeof updateUserSchema>;

// Login schema
export const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(1, "Password is required"),
});

export type LoginInput = z.infer<typeof loginSchema>;
```

```typescript
// packages/schemas/src/api.ts
import * as z from "zod";

// Generic API response wrappers
export function createSuccessResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    success: z.literal(true),
    data: dataSchema,
    meta: z.object({
      timestamp: z.iso.datetime(),
      requestId: z.string().optional(),
    }).optional(),
  });
}

export const errorResponseSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});

// Pagination schemas
export const paginationQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  perPage: z.coerce.number().int().positive().max(100).default(20),
  sortBy: z.string().optional(),
  sortOrder: z.enum(["asc", "desc"]).default("desc"),
});

export type PaginationQuery = z.infer<typeof paginationQuerySchema>;

export function createPaginatedResponseSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    data: z.array(itemSchema),
    pagination: z.object({
      page: z.number(),
      perPage: z.number(),
      total: z.number(),
      totalPages: z.number(),
    }),
  });
}
```

```typescript
// packages/schemas/src/index.ts
export * from "./user";
export * from "./product";
export * from "./api";
export * from "./utils";
```

### Backend Usage (Express/Fastify)

```typescript
// backend/src/routes/users.ts
import { Router } from "express";
import { createUserSchema, updateUserSchema, userSchema } from "@myapp/schemas";
import * as z from "zod";

const router = Router();

// Middleware for validating request body
function validateBody<T>(schema: z.ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    
    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: {
          code: "VALIDATION_ERROR",
          message: "Invalid request body",
          details: result.error.issues,
        },
      });
    }
    
    req.validatedBody = result.data;
    next();
  };
}

// Middleware for validating query params
function validateQuery<T>(schema: z.ZodSchema<T>) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.query);
    
    if (!result.success) {
      return res.status(400).json({
        success: false,
        error: {
          code: "VALIDATION_ERROR",
          message: "Invalid query parameters",
          details: result.error.issues,
        },
      });
    }
    
    req.validatedQuery = result.data;
    next();
  };
}

// Routes
router.post(
  "/users",
  validateBody(createUserSchema),
  async (req, res) => {
    const userData = req.validatedBody;
    // userData is typed as CreateUserInput
    const user = await createUser(userData);
    res.json({ success: true, data: user });
  }
);

router.patch(
  "/users/:id",
  validateBody(updateUserSchema),
  async (req, res) => {
    const updates = req.validatedBody;
    const user = await updateUser(req.params.id, updates);
    res.json({ success: true, data: user });
  }
);
```

### Frontend Usage (React)

```typescript
// frontend/src/components/UserForm.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { createUserSchema, type CreateUserInput } from "@myapp/schemas";

function UserRegistrationForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateUserInput>({
    resolver: zodResolver(createUserSchema),
  });

  const onSubmit = async (data: CreateUserInput) => {
    const response = await fetch("/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      // Handle error
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("email")} type="email" />
      {errors.email && <span>{errors.email.message}</span>}
      
      <input {...register("name")} />
      {errors.name && <span>{errors.name.message}</span>}
      
      <input {...register("password")} type="password" />
      {errors.password && <span>{errors.password.message}</span>}
      
      <button type="submit" disabled={isSubmitting}>
        Register
      </button>
    </form>
  );
}
```

### API Client with Shared Schemas

```typescript
// frontend/src/lib/api.ts
import { 
  userSchema, 
  createPaginatedResponseSchema,
  type User 
} from "@myapp/schemas";
import * as z from "zod";

const paginatedUsersSchema = createPaginatedResponseSchema(userSchema);

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async getUsers(): Promise<{ users: User[]; total: number }> {
    const response = await fetch(`${this.baseUrl}/users`);
    const json = await response.json();
    
    // Validate with shared schema
    const result = paginatedUsersSchema.parse(json);
    
    return {
      users: result.data,
      total: result.pagination.total,
    };
  }

  async getUser(id: string): Promise<User> {
    const response = await fetch(`${this.baseUrl}/users/${id}`);
    const json = await response.json();
    
    return userSchema.parse(json.data);
  }
}
```

### Database Integration (Prisma + Zod)

```typescript
// backend/src/db/schema-extensions.ts
import { Prisma } from "@prisma/client";
import { userSchema, type User } from "@myapp/schemas";

// Extend Prisma types with Zod validation
export function validateUser(data: unknown): User {
  return userSchema.parse(data);
}

// Helper for database results
export function toValidatedUser(prismaUser: Prisma.UserGetPayload<{}>): User {
  return userSchema.parse({
    id: prismaUser.id,
    email: prismaUser.email,
    name: prismaUser.name,
    avatar: prismaUser.avatar,
    createdAt: prismaUser.createdAt.toISOString(),
    updatedAt: prismaUser.updatedAt.toISOString(),
  });
}
```

### Build Configuration

```json
// packages/schemas/package.json
{
  "name": "@myapp/schemas",
  "version": "1.0.0",
  "main": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "scripts": {
    "build": "tsup src/index.ts --format cjs,esm --dts",
    "dev": "tsup src/index.ts --format cjs,esm --dts --watch"
  },
  "dependencies": {
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "tsup": "^8.0.0",
    "typescript": "^5.3.0"
  }
}
```

```json
// frontend/package.json (excerpt)
{
  "dependencies": {
    "@myapp/schemas": "workspace:*",
    "react-hook-form": "^7.49.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0"
  }
}
```

```json
// backend/package.json (excerpt)
{
  "dependencies": {
    "@myapp/schemas": "workspace:*",
    "express": "^4.18.0",
    "zod": "^3.22.0"
  }
}
```

---

## Summary

This guide covers the essential Zod validation patterns for React applications:

1. **Schema Definition** - Use primitives, coercion, composition patterns
2. **Form Integration** - React Hook Form with `zodResolver` for type-safe forms
3. **API Validation** - Validate all external data at runtime boundaries
4. **Type Inference** - Extract TypeScript types automatically from schemas
5. **Error Handling** - Custom messages at schema, parse, or global level
6. **Complex Patterns** - Objects, arrays, unions, discriminated unions, records
7. **Transformations** - Preprocess, transform, codecs for data conversion
8. **Async Validation** - Refinements and transforms with async operations
9. **Environment Variables** - Type-safe env validation with stringbool
10. **Shared Schemas** - Monorepo structure for frontend/backend reuse

### Key Best Practices

- Always validate external data (API responses, user input)
- Use `safeParse` for user-facing validation, `parse` for internal validation
- Extract types with `z.infer<>` to keep TypeScript and Zod in sync
- Use discriminated unions over regular unions for better performance
- Share schemas between frontend and backend in a monorepo setup
- Use coercion for form data that arrives as strings
- Implement custom error messages for better UX
- Leverage transforms to normalize data at validation time
