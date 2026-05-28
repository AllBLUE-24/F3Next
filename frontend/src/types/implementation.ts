// src/types/implementation.ts

export type ImplementationStep = 'upload' | 'analyze' | 'validate' | 'import';

export type DeploymentStatus = 'pending' | 'deploying' | 'ready' | 'failed';

export type AnalysisTaskStatus = 'idle' | 'running' | 'done' | 'needs_input' | 'failed';

export type ValidationItemType = 'missing' | 'contradiction' | 'suggestion';

export interface ImplementationSession {
  id: string;
  companySlug: string;
  userSlug: string;
  currentStep: ImplementationStep;
  instanceId: string;
  analysisJobId: string | null;
  createdAt: string;
}

export interface DeploymentState {
  status: DeploymentStatus;
  progress: number; // 0–100
  instanceUrl: string | null;
  region: string;
  erpSoftware: string; // e.g. "ERPNext"
  startedAt: string;
  readyAt: string | null;
  adminPassword?: string | null;
}

export interface AnalysisTask {
  id: string;
  label: string;
  status: AnalysisTaskStatus;
  detail: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface ValidationItem {
  id: string;
  type: ValidationItemType;
  field: string;
  message: string;
  required: boolean;
  resolved: boolean;
  userResponse: string | null;
}

export interface CompanyProfile {
  name: string;
  legalName: string;
  industry: string;
  subIndustry: string | null;
  size: string;
  employeeCount: number | null;
  currency: string;
  fiscalYearStart: string;
  country: string;
  state: string | null;
  gstNumber: string | null;
  modules: string[];
  warehouses: string[];
  costCenters: string[];
  confidence: number; // 0–100, how confident the AI is in this profile
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'queued' | 'uploading' | 'uploaded' | 'error';
  progress: number;
  error: string | null;
}

/** @deprecated use LiveInstance */
export type SandboxInstance = LiveInstance;

export interface LiveInstance {
  url: string;
  username: string;
  password: string;
  isApproved: boolean;
}

export interface ImplementationContextValue {
  session: ImplementationSession;
  deployment: DeploymentState;
  profile: CompanyProfile | null;
  validationItems: ValidationItem[];
  liveInstance: LiveInstance | null;
  refreshDeployment: () => void;
}