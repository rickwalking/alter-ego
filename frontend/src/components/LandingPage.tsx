import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

/**
 * Landing Page component with project introduction
 *
 * Features liquid glass morphism design with responsive layout
 */
export function LandingPage() {
  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-3xl font-bold text-primary-400 mb-2">
            Alter Ego
          </CardTitle>
          <CardDescription className="text-lg text-text-secondary">
            AI-Powered Personal Chatbot
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-text-primary leading-relaxed">
            Welcome to my AI assistant! I'm here to answer questions about my professional background,
            skills, and experience. Whether you're a recruiter or just curious, feel free to ask me
            anything about my career journey.
          </p>

          <div className="pt-2 space-y-2">
            <h3 className="text-sm font-semibold text-primary-300 uppercase tracking-wide">
              What you can ask:
            </h3>
            <ul className="space-y-1 text-sm text-text-secondary">
              <li className="flex items-start hover:text-primary-300 transition-colors cursor-pointer group">
                <span className="text-primary-500 mr-2 group-hover:text-primary-400">•</span>
                <span>Technical skills and expertise</span>
              </li>
              <li className="flex items-start hover:text-primary-300 transition-colors cursor-pointer group">
                <span className="text-primary-500 mr-2 group-hover:text-primary-400">•</span>
                <span>Work experience and projects</span>
              </li>
              <li className="flex items-start hover:text-primary-300 transition-colors cursor-pointer group">
                <span className="text-primary-500 mr-2 group-hover:text-primary-400">•</span>
                <span>Education and certifications</span>
              </li>
              <li className="flex items-start hover:text-primary-300 transition-colors cursor-pointer group">
                <span className="text-primary-500 mr-2 group-hover:text-primary-400">•</span>
                <span>Career goals and interests</span>
              </li>
            </ul>
          </div>

          <div className="pt-4 flex items-center gap-2 text-xs text-text-tertiary">
            <span className="inline-block w-2 h-2 rounded-full bg-success animate-pulse"></span>
            <span>AI Assistant Ready</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
