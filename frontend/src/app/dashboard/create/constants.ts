export const CREATE_STEPS = [
  { num: 1, label: "Brief" },
  { num: 2, label: "Research" },
  { num: 3, label: "Outline" },
  { num: 4, label: "Content" },
  { num: 5, label: "Images" },
  { num: 6, label: "Review" },
  { num: 7, label: "Publish" },
];

export const CREATE_TEMPLATES = [
  { icon: "📊", name: "Analysis", desc: "Deep dive with data" },
  { icon: "⚖️", name: "Comparison", desc: "Side by side" },
  { icon: "📚", name: "Tutorial", desc: "Step by step" },
  { icon: "📰", name: "News Flash", desc: "Quick update" },
  { icon: "🧠", name: "Deep Dive", desc: "Comprehensive" },
  { icon: "🎯", name: "Listicle", desc: "Top N format" },
];

export const CREATE_ARTIFACTS = [
  {
    name: "Research Report",
    desc: "Collecting data from Twitter, GitHub, tech blogs, and documentation...",
    status: "pending",
  },
  {
    name: "Slide Outline",
    desc: "Generating structured outline with slide-by-slide breakdown...",
    status: "pending",
  },
  {
    name: "Slide Content",
    desc: "Drafting content with persona voice matching...",
    status: "pending",
  },
  {
    name: "Design Tokens",
    desc: "Generating color palette, typography, and layout tokens...",
    status: "pending",
  },
  {
    name: "Generated Images",
    desc: "Creating custom images with selected model and style...",
    status: "pending",
  },
  {
    name: "Final Review",
    desc: "Quality check, persona enforcement, and rubric validation...",
    status: "pending",
  },
];

export const CREATE_SUMMARY_ROWS = [
  { label: "Type", value: "Analysis" },
  { label: "Slides", value: "1 intro, 3 content, 1 closing, 1 CTA" },
  { label: "Aspect Ratio", value: "1080x1350" },
  { label: "Language", value: "pt-BR" },
  { label: "Generate Images", value: "Yes" },
  { label: "Status", value: "Draft", badge: true },
] as const;
