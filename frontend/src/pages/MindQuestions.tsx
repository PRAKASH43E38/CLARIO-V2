import { FormEvent, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../components';
import { useAuth } from '../hooks';
import { api } from '../services';
import { cn } from '../utils/helpers';

const QUESTIONS = [
  {
    key: 'learning_motivation',
    label: 'What usually motivates you to learn something new?',
    options: ['Solving a real problem', 'Curiosity', 'Career or study goals', 'Making something myself'],
  },
  {
    key: 'preferred_explanation',
    label: 'What helps a new idea make sense?',
    options: ['A worked example', 'A clear step-by-step explanation', 'An analogy or visual', 'Trying it hands-on'],
  },
  {
    key: 'support_when_stuck',
    label: 'When you get stuck, what support is most useful?',
    options: ['A small hint', 'A different explanation', 'A simpler example', 'A short practice task'],
  },
  {
    key: 'feedback_preference',
    label: 'What kind of feedback helps you improve?',
    options: ['Direct correction', 'Encouragement plus an explanation', 'A hint to reconsider', 'Show me a model answer'],
  },
  {
    key: 'challenge_preference',
    label: 'How would you like challenges to progress?',
    options: ['Start gently and build up', 'Keep a steady pace', 'Challenge me when I am ready', 'Let me choose when to go deeper'],
  },
] as const;

type MindAnswers = {
  learning_motivation: string;
  preferred_explanation: string;
  support_when_stuck: string;
  feedback_preference: string;
  challenge_preference: string;
};

const EMPTY_ANSWERS: MindAnswers = {
  learning_motivation: '',
  preferred_explanation: '',
  support_when_stuck: '',
  feedback_preference: '',
  challenge_preference: '',
};

export function MindQuestionsPage() {
  const navigate = useNavigate();
  const { userId, profileComplete, mindProfileComplete, refreshAuthStatus } = useAuth();
  const [answers, setAnswers] = useState<MindAnswers>(EMPTY_ANSWERS);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    if (!profileComplete) {
      navigate('/profile-setup', { replace: true });
    } else if (mindProfileComplete) {
      navigate('/dashboard', { replace: true });
    }
  }, [userId, profileComplete, mindProfileComplete, navigate]);

  if (!userId) return null;
  if (!profileComplete) return null;
  if (mindProfileComplete) return null;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await api.saveMindProfile(userId, answers);
      await refreshAuthStatus();
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save your Mind Profile.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-clario-bg-50 px-4 py-12 flex items-center justify-center">
      <Card variant="default" className="mx-auto w-full max-w-2xl shadow-[0_6px_0_#E5E5E5]" padding="lg">
        <div className="text-center mb-8">
          <p className="font-black uppercase tracking-widest text-clario-primary-600 text-xs mb-2">Step 2 of 2 · Asked once</p>
          <h1 className="text-3xl font-black text-clario-surface-900 tracking-tight">Your learning Mind Profile</h1>
          <p className="mt-2 text-clario-surface-600 font-semibold">These answers will be saved to your profile; we won't ask them again in every session.</p>
        </div>

        <form className="space-y-8" onSubmit={handleSubmit}>
          {QUESTIONS.map(question => (
            <fieldset key={question.key} className="space-y-3">
              <legend className="text-lg font-black text-clario-surface-900 mb-4">{question.label}</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {question.options.map(option => (
                  <label
                    key={option}
                    className={cn(
                      "flex cursor-pointer items-center gap-3 rounded-clario-md border-2 p-4 transition-all duration-150 font-bold text-sm",
                      answers[question.key] === option
                        ? "border-clario-green bg-clario-green-t text-clario-green-deep shadow-[inset_0_-2px_0_#58CC02]"
                        : "border-clario-line bg-white hover:border-clario-green-t text-clario-surface-700 hover:bg-clario-bg-50"
                    )}
                  >
                    <input
                      type="radio"
                      name={question.key}
                      value={option}
                      checked={answers[question.key] === option}
                      onChange={() => setAnswers(previous => ({ ...previous, [question.key]: option }))}
                      className="w-4 h-4 text-clario-green focus:ring-clario-green-t"
                      required
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

          {error && (
            <div className="p-4 bg-clario-red-t border-2 border-clario-red-sh rounded-clario-md text-clario-red-sh font-bold text-sm animate-shake">
              <span className="mr-2">⚠️</span> {error}
            </div>
          )}

          <div className="pt-4">
            <Button type="submit" variant="primary" fullWidth className="py-4 text-lg" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Finish setup'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
