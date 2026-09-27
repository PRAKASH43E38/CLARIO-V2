import { useEffect, useState } from 'react';
import { Card, Badge, ProgressBar, ConceptNode, ConceptPath, LoadingSpinner, SkeletonRoadmap, EmptyState, CircularProgress } from '../components';
import { useRoadmap } from '../hooks';
import { useAuth } from '../hooks';
import { cn } from '../utils/helpers';
import { 
  Target, CheckCircle, AlertCircle, BookOpen, 
  TrendingUp, ArrowRight, Lock, Brain, Zap 
} from 'lucide-react';

const statusIcons: Record<string, any> = {
  mastered: CheckCircle,
  remediating: AlertCircle,
  learning: BookOpen,
  upcoming: Lock,
};

export function RoadmapPage() {
  const { userId, profile } = useAuth();
  const { roadmap, isLoading, error, refetch } = useRoadmap(userId);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [showConceptDetail, setShowConceptDetail] = useState(false);

  useEffect(() => {
    if (userId) {
      refetch();
    }
  }, [userId, refetch]);

  if (isLoading) {
    return <SkeletonRoadmap />;
  }

  if (error) {
    return (
      <div className="page-container max-w-3xl">
        <EmptyState
          title="Unable to load roadmap"
          message={error}
          action={{ label: 'Retry', onClick: refetch }}
        />
      </div>
    );
  }

  if (!roadmap || roadmap.roadmap.length === 0) {
    return (
      <div className="page-container max-w-3xl">
        <EmptyState
          title="No learning path yet"
          message="Complete onboarding to generate your personalized roadmap"
          action={{ label: 'Start Onboarding', onClick: () => window.location.href = '/onboarding' }}
        />
      </div>
    );
  }

  const masteredCount = roadmap.roadmap.filter(c => c.status === 'mastered').length;
  const totalCount = roadmap.roadmap.length;
  const progress = totalCount > 0 ? (masteredCount / totalCount) * 100 : 0;

  return (
    <div className="page-container max-w-3xl">
      {/* Header */}
      <div className="mb-8 animate-slide-up">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <p className="text-clario-primary-600 font-medium">Your Learning Journey</p>
            <h1 className="font-display font-bold text-3xl text-clario-surface-900 mt-1">{roadmap.current_topic}</h1>
          </div>
          <div className="flex items-center gap-3">
            <ProgressBar value={progress} max={100} size="sm" className="w-48" variant="success" />
            <Badge variant="success" size="lg">{masteredCount}/{totalCount} Mastered</Badge>
          </div>
        </div>

        {/* Progress Overview */}
        <Card padding="lg" className="bg-gradient-to-br from-clario-primary-50 to-clario-secondary-50 border-clario-primary-100">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="text-center p-4 bg-white/80 backdrop-blur rounded-2xl shadow-soft">
              <CircularProgress value={progress} size={80} strokeWidth={6} variant="success" showValue={true} />
              <p className="mt-2 text-sm text-clario-success-600 font-medium">Overall Mastery</p>
            </div>
            <div className="text-center p-4 bg-white/80 backdrop-blur rounded-2xl shadow-soft">
              <p className="font-display font-bold text-3xl text-clario-primary-600">{masteredCount}</p>
              <p className="text-sm text-clario-surface-500">Concepts Mastered</p>
            </div>
            <div className="text-center p-4 bg-white/80 backdrop-blur rounded-2xl shadow-soft">
              <p className="font-display font-bold text-3xl text-clario-warning-600">
                {roadmap.roadmap.filter(c => c.status === 'remediating').length}
              </p>
              <p className="text-sm text-clario-surface-500">Need Practice</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Roadmap Path */}
      <div className="animate-slide-up">
        <ConceptPath
          concepts={roadmap.roadmap.map(c => ({
            id: c.concept_id,
            title: c.concept_title,
            status: c.status,
            difficulty: c.difficulty,
            isCurrent: c.is_next,
            isNext: c.is_next,
          }))}
          onConceptClick={(conceptId) => {
            setSelectedConcept(conceptId);
            setShowConceptDetail(true);
          }}
        />
      </div>

      {/* Concept Details Modal */}
      {showConceptDetail && selectedConcept && (
        <ConceptDetailModal
          concept={roadmap.roadmap.find(c => c.concept_id === selectedConcept)!}
          onClose={() => {
            setShowConceptDetail(false);
            setSelectedConcept(null);
          }}
        />
      )}
    </div>
  );
}

function ConceptDetailModal({ concept, onClose }: { concept: any; onClose: () => void }) {
  const Icon = statusIcons[concept.status] || BookOpen;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl shadow-elevated max-w-md w-full max-h-[90vh] overflow-y-auto animate-scale-in">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="font-display font-bold text-xl text-clario-surface-900">{concept.concept_title}</h2>
              <Badge status={concept.status} size="md" className="mt-2" />
            </div>
            <button onClick={onClose} className="p-2 rounded-xl text-clario-surface-400 hover:text-clario-surface-600 hover:bg-clario-surface-100 transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-clario-surface-50 rounded-xl">
              <div className="w-12 h-12 rounded-xl bg-clario-primary-100 text-clario-primary-600 flex items-center justify-center">
                <Icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm text-clario-surface-500">Difficulty</p>
                <p className="font-display font-bold text-xl text-clario-surface-900">Level {concept.difficulty} / 5</p>
              </div>
            </div>

            <div className="pt-4 border-t border-clario-surface-100">
              <p className="text-sm font-medium text-clario-surface-700 mb-2">Status Details</p>
              <div className="space-y-2 text-sm">
                {concept.status === 'mastered' && (
                  <div className="flex items-center gap-2 text-clario-success-700 bg-clario-success-50 p-3 rounded-xl">
                    <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    <span>You have mastered this concept. Ready for the next challenge!</span>
                  </div>
                )}
                {concept.status === 'remediating' && (
                  <div className="flex items-center gap-2 text-clario-warning-700 bg-clario-warning-50 p-3 rounded-xl">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span>This concept needs more practice. A targeted session will help you master it.</span>
                  </div>
                )}
                {concept.status === 'learning' && (
                  <div className="flex items-center gap-2 text-clario-primary-700 bg-clario-primary-50 p-3 rounded-xl">
                    <BookOpen className="w-5 h-5 flex-shrink-0" />
                    <span>Currently learning this concept. Keep going!</span>
                  </div>
                )}
                {concept.status === 'upcoming' && (
                  <div className="flex items-center gap-2 text-clario-surface-600 bg-clario-surface-50 p-3 rounded-xl">
                    <Lock className="w-5 h-5 flex-shrink-0" />
                    <span>This concept will unlock after you master the previous ones.</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t border-clario-surface-100 flex gap-3">
              <button 
                onClick={onClose}
                className="flex-1 btn-secondary"
              >
                Close
              </button>
              {(concept.status === 'learning' || concept.status === 'remediating') && (
                <button 
                  onClick={() => { onClose(); window.location.href = '/learn'; }}
                  className="flex-1 btn-primary"
                >
                  Practice Now
                  <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}