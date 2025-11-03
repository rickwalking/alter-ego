import { LandingPage } from '@/components/LandingPage';
import { ChatInterface } from '@/components/ChatInterface';

/**
 * Main Application Component
 *
 * Layout:
 * - Desktop: Two-column grid with LandingPage and ChatInterface side by side
 * - Mobile/Tablet: Stacked layout with LandingPage on top, ChatInterface below
 */
function App() {
  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Main Container */}
      <div className="container mx-auto px-4 py-8">
        {/* Responsive Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Landing Page Section */}
          <div className="flex items-start">
            <LandingPage />
          </div>

          {/* Chat Interface Section */}
          <div className="flex items-start">
            <ChatInterface />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
