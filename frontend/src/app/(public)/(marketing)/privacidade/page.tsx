import type { Metadata } from "next";
import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";
import { MarketingFooter } from "@/app/(public)/(marketing)/marketing-footer";
import { NEON_CYAN, TEXT, TEXT_MUTED } from "@/constants/neon";
import { SOCIAL_LINKS } from "@/constants/social";
import { pageMetadata } from "@/lib/page-metadata";

/** The policy is written in Portuguese only; every visitor reads that text. */
const POLICY_LOCALE = "pt";
const POLICY_LANG = "pt-BR";
const PRIVACY_NAMESPACE = "privacy";
const HOME_NAMESPACE = "home";
const PRIVACY_MAX_WIDTH_PX = 760;

type PolicyTranslator = Awaited<ReturnType<typeof getTranslations>>;

interface PolicyTranslators {
  t: PolicyTranslator;
  home: PolicyTranslator;
}

const strong = (chunks: ReactNode): ReactNode => <strong>{chunks}</strong>;

const linkedIn = (chunks: ReactNode): ReactNode => (
  <a
    href={SOCIAL_LINKS.LINKEDIN}
    target="_blank"
    rel="noopener noreferrer"
    style={{ color: NEON_CYAN }}
    className="underline underline-offset-4"
  >
    {chunks}
  </a>
);

/** Title and Open Graph tags of the privacy policy. */
export async function generateMetadata(): Promise<Metadata> {
  return pageMetadata("privacy");
}

function PolicySection({
  heading,
  children,
}: Readonly<{ heading: string; children: ReactNode }>): React.ReactElement {
  return (
    <section className="mt-10 space-y-4">
      <h2 className="text-2xl font-bold" style={{ color: TEXT }}>
        {heading}
      </h2>
      {children}
    </section>
  );
}

function DataSection({
  t,
}: Readonly<{ t: PolicyTranslator }>): React.ReactElement {
  return (
    <PolicySection heading={t("data.heading")}>
      <ul className="list-disc space-y-2 pl-6">
        <li>{t.rich("data.visits", { strong })}</li>
        <li>{t.rich("data.chat", { strong })}</li>
        <li>{t.rich("data.meta", { strong })}</li>
      </ul>
      <p>{t("data.closing")}</p>
    </PolicySection>
  );
}

function PolicyBody({
  t,
}: Readonly<{ t: PolicyTranslator }>): React.ReactElement {
  return (
    <>
      <PolicySection heading={t("about.heading")}>
        <p>{t("about.intro")}</p>
        <p>{t.rich("about.metaApp", { strong })}</p>
      </PolicySection>
      <DataSection t={t} />
      <PolicySection heading={t("retention.heading")}>
        <p>{t("retention.body")}</p>
      </PolicySection>
      <PolicySection heading={t("rights.heading")}>
        <p>{t.rich("rights.body", { link: linkedIn })}</p>
      </PolicySection>
    </>
  );
}

/** The policy and footer translators, always in the policy's language. */
export async function loadPolicyTranslators(): Promise<PolicyTranslators> {
  const [t, home] = await Promise.all([
    getTranslations({ locale: POLICY_LOCALE, namespace: PRIVACY_NAMESPACE }),
    getTranslations({ locale: POLICY_LOCALE, namespace: HOME_NAMESPACE }),
  ]);
  return { t, home };
}

/** The policy article and the marketing footer. */
export function PrivacyPolicyView({
  t,
  home,
}: Readonly<PolicyTranslators>): React.ReactElement {
  return (
    <>
      <article
        lang={POLICY_LANG}
        className="mx-auto px-6 py-16 text-base leading-relaxed"
        style={{ maxWidth: `${PRIVACY_MAX_WIDTH_PX}px`, color: TEXT_MUTED }}
      >
        <h1
          className="text-4xl font-extrabold tracking-tight sm:text-5xl"
          style={{ color: TEXT }}
        >
          {t("title")}
        </h1>
        <p className="mt-4 text-sm">{t("updated")}</p>
        <PolicyBody t={t} />
      </article>
      <MarketingFooter privacyLabel={home("footer.privacy")} />
    </>
  );
}

/** The public privacy policy (`/privacidade`), server-rendered for crawlers. */
export default async function PrivacyPolicyPage(): Promise<React.ReactElement> {
  return <PrivacyPolicyView {...await loadPolicyTranslators()} />;
}
