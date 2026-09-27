import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card } from '../components';
import { useAuth } from '../hooks';

export function ProfilePage() {
  const navigate = useNavigate();
  const { userProfile, refreshUserProfile, logout, userId } = useAuth();

  useEffect(() => {
    if (userId) void refreshUserProfile();
  }, [refreshUserProfile, userId]);

  const handleLogout = () => {
    logout();
    navigate('/auth', { replace: true });
  };

  return (
    <div className="page-container max-w-3xl">
      <Card padding="lg">
        <p className="font-bold text-clario-primary-600">Account</p>
        <h1 className="mt-2 text-3xl font-black text-clario-surface-900">Your profile</h1>
        {!userProfile ? (
          <p className="mt-4 text-clario-surface-600">Profile details load aagudhu...</p>
        ) : (
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-clario-surface-500">Name</dt>
              <dd className="font-bold text-clario-surface-900">{userProfile.name}</dd>
            </div>
            <div>
              <dt className="text-sm text-clario-surface-500">Email</dt>
              <dd className="font-bold text-clario-surface-900">{userProfile.email}</dd>
            </div>
            <div>
              <dt className="text-sm text-clario-surface-500">Gender</dt>
              <dd className="font-bold text-clario-surface-900">{userProfile.gender.replace(/_/g, ' ')}</dd>
            </div>
            <div>
              <dt className="text-sm text-clario-surface-500">Sign-in method</dt>
              <dd className="font-bold capitalize text-clario-surface-900">{userProfile.authentication_provider}</dd>
            </div>
            {userProfile.basic_details && (
              <div className="sm:col-span-2">
                <dt className="text-sm text-clario-surface-500">About you</dt>
                <dd className="font-bold text-clario-surface-900">{userProfile.basic_details}</dd>
              </div>
            )}
          </dl>
        )}
        <Button className="mt-8" variant="ghost" onClick={handleLogout}>Sign out</Button>
      </Card>
    </div>
  );
}
