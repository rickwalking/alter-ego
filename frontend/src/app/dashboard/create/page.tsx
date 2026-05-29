"use client";

import { useState } from "react";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import {
  CreateTemplateSection,
  CreateThemeSection,
  CreateTopicSection,
} from "@/app/dashboard/create/create-form-sections";
import { CreateSidebar } from "@/app/dashboard/create/create-sidebar";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";

export default function CreateCarouselPage(): React.ReactElement {
  const [selectedTemplate, setSelectedTemplate] = useState(0);

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Create Carousel"
        breadcrumb={[{ label: "new project" }]}
      />

      <div className="p-7">
        <CreateProgressSteps />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 360px",
            gap: "24px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            <CreateTopicSection />
            <CreateTemplateSection
              selectedTemplate={selectedTemplate}
              onSelectTemplate={setSelectedTemplate}
            />
            <CreateThemeSection />
          </div>
          <CreateSidebar />
        </div>
      </div>
    </div>
  );
}
