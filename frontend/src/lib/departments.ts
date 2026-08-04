/** Department options for team invites and cascade routing (mirrors shared/erp_policies/departments.py). */

export const DEPARTMENTS = [
  { value: "sales", label: "Sales" },
  { value: "purchase", label: "Purchase" },
  { value: "production", label: "Production" },
  { value: "accounts", label: "Accounts" },
  { value: "stores", label: "Stores / Inventory" },
  { value: "projects", label: "Projects" },
  { value: "admin", label: "Admin" },
] as const;

export type DepartmentValue = (typeof DEPARTMENTS)[number]["value"];

export function departmentLabel(value: string | null | undefined): string {
  if (!value) return "Unassigned";
  return DEPARTMENTS.find((d) => d.value === value)?.label ?? value;
}
