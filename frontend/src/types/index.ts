// Shared frontend types. Kept in sync with backend/app/schemas as the API
// lands in later phases -- this is a hand-written mirror, not generated,
// per the "keep it simple / easy to inspect" principle in the spec.

export type Distribution = "ubuntu" | "rocky" | "debian" | "alpine";

export type InstanceStatus =
  | "CREATING"
  | "RUNNING"
  | "TERMINATING"
  | "TERMINATED"
  | "EXPIRED"
  | "ERROR";

export interface Instance {
  id: string;
  distribution: Distribution;
  status: InstanceStatus;
  namespace: string;
  pod_name: string;
  duration_minutes: number;
  credits_charged: number;
  created_at: string;
  expires_at: string;
  terminated_at: string | null;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  transaction_type: string;
  description: string;
  created_at: string;
}

export interface CurrentUser {
  username: string;
  is_admin: boolean;
  credit_balance: number;
}
