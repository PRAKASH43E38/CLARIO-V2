import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../components';
import { useAuth } from '../hooks';
import { api } from '../services';

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

  if (!userId) return null;
  if (!profileComplete) {
    navigate('/profile-setup', { replace: true });
    return null;
  }
  if (mindProfileComplete) {
    navigate('/dashboard', { replace: true });
    return null;
  }

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
    <div className="min-h-screen bg-clario-bg-50 px-4 py-10">
      <Card className="mx-auto max-w-2xl" padding="lg">
        <p className="font-bold text-clario-primary-600">Step 2 of 2 · Asked once</p>
        <h1 className="mt-2 text-3xl font-black text-clario-surface-900">Your learning Mind Profile</h1>
        <p className="mt-2 text-clario-surface-600">Indha answers unga profile-la save aagum; every session-layum repeat panna maattom.</p>
        <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
          {QUESTIONS.map(question => (
            <fieldset key={question.key}>
              <legend className="mb-2 font-bold text-clario-surface-900">{question.label}</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {question.options.map(option => (
                  <label key={option} className="flex cursor-pointer items-center gap-3 rounded-xl border border-clario-surface-200 bg-white p-3">
                    <input
                      type="radio"
                      name={question.key}
                      value={option}
                      checked={answers[question.key] === option}
                      onChange={() => setAnswers(previous => ({ ...previous, [question.key]: option }))}
                      required
                    />
                    <span>{option}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
          {error && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{error}</p>}
          <Button type="submit" variant="primary" fullWidth disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Finish setup'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
