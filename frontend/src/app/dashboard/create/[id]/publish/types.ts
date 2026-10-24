import type { LoadedProject } from "./use-publish-page";

/** The publish step's cover picker: the carousel, its loaded project and the refresh. */
export interface PublishCoverPickerProps {
  projectId: string;
  project: LoadedProject;
  onSwitched: (artifactVersion: string | null) => void;
}
