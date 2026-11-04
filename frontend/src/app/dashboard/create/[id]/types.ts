/** The recovery controls of a workspace step and the Retry's toast. */
export interface WorkspaceRecovery {
  reprocessControl: React.ReactNode;
  retryControl: React.ReactNode;
  retryPending: boolean;
  startOverLabel: string;
  retryToast: React.ReactNode;
}
