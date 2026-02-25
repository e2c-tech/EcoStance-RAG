import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { Icons } from '../components/icons';
import { useAuth } from '../context/AuthContext.v2';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      console.log('🔐 Starting login process...');

      // Try the actual login through AuthContext
      await login(email, password);
      console.log('✅ Login successful, navigating to dashboard...');
      navigate('/');
    } catch (error: unknown) {
      console.error("❌ Login failed:", error);
      const errorMessage = error instanceof Error ? error.message : 'Login failed. Please check your credentials.';
      setError(errorMessage);

    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-primary">Welcome Back</h1>
          <p className="text-sm text-text-secondary">Log in to your account to continue</p>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          <div>
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <Icons.EyeOff className="h-4 w-4" />
                ) : (
                  <Icons.Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Icons.Spinner className="h-4 w-4 animate-spin mr-2" />
                Logging in...
              </>
            ) : (
              'Log In'
            )}
          </Button>
        </form>
        <div className="text-center text-sm text-text-secondary">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={() => navigate('/register')}
            className="text-primary hover:underline font-medium"
          >
            Sign Up
          </button>
        </div>

        <div className="pt-4 border-t border-border">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => navigate('/admin/login')}
          >
            <Icons.Shield className="h-4 w-4 mr-2" />
            Admin Login
          </Button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
