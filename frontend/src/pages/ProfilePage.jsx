import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { User, Mail, Award, Calendar } from 'lucide-react';

const ProfilePage = () => {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="min-h-screen py-8" data-testid="profile-page">
      <div className="container mx-auto px-4 max-w-2xl">
        <h1 className="text-3xl md:text-4xl font-bold mb-8">My Profile</h1>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-4">
              {user.picture ? (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-20 h-20 rounded-full"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center">
                  <span className="text-3xl font-bold text-primary-foreground">
                    {user.name?.charAt(0)?.toUpperCase()}
                  </span>
                </div>
              )}
              <div>
                <CardTitle className="text-2xl">{user.name}</CardTitle>
                <Badge className="mt-1">
                  {user.role?.charAt(0).toUpperCase() + user.role?.slice(1)}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium">{user.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Award className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Loyalty Points</p>
                <p className="font-medium">{user.loyalty_points || 0} points</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Member Since</p>
                <p className="font-medium">
                  {user.created_at 
                    ? new Date(user.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })
                    : 'N/A'}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-border">
              <h3 className="font-semibold mb-3">Loyalty Rewards</h3>
              <div className="p-4 rounded-xl bg-muted">
                <p className="text-sm text-muted-foreground mb-2">
                  Earn 1 point for every $1 spent. Redeem points for discounts!
                </p>
                <div className="flex items-center justify-between">
                  <span className="font-medium">Current Points</span>
                  <span className="text-xl font-bold text-primary">
                    {user.loyalty_points || 0}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProfilePage;
