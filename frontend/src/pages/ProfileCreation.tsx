import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Input } from '../components';
import { useAuth } from '../hooks';
import { api } from '../services';

export function ProfileCreationPage() {
  const navigate = useNavigate();
  const { userId, profileComplete, refreshAuthStatus, refreshUserProfile } = useAuth();
  const [name, setName] = useState('');
  const [gender, setGender] = useState('');
  const [basicDetails, setBasicDetails] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!userId) return null;
  if (profileComplete) {
    navigate('/mind-profile', { replace: true });
    return null;
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await api.saveUserProfile(userId, { name, gender, basic_details: basicDetails });
      await Promise.all([refreshAuthStatus(), refreshUserProfile()]);
      navigate('/mind-profile', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save your profile.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-clario-bg-50 px-4 py-10">
      <Card className="mx-auto max-w-xl" padding="lg">
        <p className="font-bold text-clario-primary-600">Step 1 of 2</p>
        <h1 className="mt-2 text-3xl font-black text-clario-surface-900">Create your profile</h1>
        <p className="mt-2 text-clario-surface-600">A few details help us personalize your learning space.</p>
        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="label" htmlFor="profile-name">Name</label>
            <Input id="profile-name" value={name} onChange={event => setName(event.target.value)} required maxLength={100} />
          </div>
          <div>
            <label className="label" htmlFor="profile-gender">Gender</label>
            <select id="profile-gender" className="input" value={gender} onChange={event => setGender(event.target.value)} required>
              <option value="">Choose an option</option>
              <option value="woman">Woman</option>
              <option value="man">Man</option>
              <option value="non_binary">Non-binary</option>
              <option value="prefer_not_to_say">Prefer not to say</option>
              <option value="self_described">Self-describe in basic details</option>
            </select>
          </div>
          <div>
            <label className="label" htmlFor="profile-details">Anything else you want us to know? (optional)</label>
            <textarea
              id="profile-details"
              className="input min-h-24"
              maxLength={1000}
              value={basicDetails}
              onChange={event => setBasicDetails(event.target.value)}
            />
          </div>
          {error && <p role="alert" className="rounded-xl bg-clario-attention-50 p-3 text-clario-attention-700">{error}</p>}
          <Button type="submit" variant="primary" fullWidth disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Continue to Mind Profile'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
