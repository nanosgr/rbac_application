'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { userService } from '@/lib/api/services';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Card from '@/components/common/Card';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import { UpdateUserDTO } from '@/types';

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const { success, error: showError } = useToast();
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const [profileData, setProfileData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || '',
  });

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const [profileError, setProfileError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    if (user) {
      setProfileData({
        full_name: user.full_name,
        email: user.email,
      });
    }
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError('');

    if (!user) return;

    try {
      const updateData: UpdateUserDTO = {
        full_name: profileData.full_name,
        email: profileData.email,
      };

      const updatedUser = await userService.update(user.id, updateData);
      setUser(updatedUser);
      setIsEditingProfile(false);
      success('Perfil actualizado exitosamente');
    } catch (error) {
      console.error('Error updating profile:', error);
      setProfileError(error instanceof Error ? error.message : 'Error al actualizar el perfil');
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');

    if (!user) return;

    // Validate password match
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('Las contraseñas no coinciden');
      return;
    }

    if (passwordData.newPassword.length < 6) {
      setPasswordError('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    try {
      const updateData: UpdateUserDTO = {
        password: passwordData.newPassword,
      };

      await userService.update(user.id, updateData);
      setIsChangingPassword(false);
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      success('Contraseña actualizada exitosamente');
    } catch (error) {
      console.error('Error updating password:', error);
      setPasswordError(error instanceof Error ? error.message : 'Error al actualizar la contraseña');
    }
  };

  if (!user) {
    return (
      <DashboardLayout title="Mi Perfil">
        <Card>
          <p>Cargando...</p>
        </Card>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Mi Perfil">
      <div className="space-y-6">
        {/* Profile Information */}
        <Card
          title="Información Personal"
          actions={
            !isEditingProfile && (
              <Button variant="secondary" onClick={() => setIsEditingProfile(true)}>
                ✏️ Editar
              </Button>
            )
          }
        >
          {isEditingProfile ? (
            <form onSubmit={handleProfileSubmit} className="space-y-4">
              {profileError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {profileError}
                </div>
              )}

              <Input
                label="Nombre Completo"
                value={profileData.full_name}
                onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                required
              />

              <Input
                label="Email"
                type="email"
                value={profileData.email}
                onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                required
              />

              <div className="flex space-x-3 pt-4">
                <Button type="submit">Guardar Cambios</Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIsEditingProfile(false);
                    setProfileData({
                      full_name: user.full_name,
                      email: user.email,
                    });
                    setProfileError('');
                  }}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Usuario
                </label>
                <p className="text-gray-900">{user.username}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre Completo
                </label>
                <p className="text-gray-900">{user.full_name}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <p className="text-gray-900">{user.email}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Estado
                </label>
                <span
                  className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                    user.is_active
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {user.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
            </div>
          )}
        </Card>

        {/* Change Password */}
        <Card
          title="Cambiar Contraseña"
          actions={
            !isChangingPassword && (
              <Button variant="secondary" onClick={() => setIsChangingPassword(true)}>
                🔒 Cambiar
              </Button>
            )
          }
        >
          {isChangingPassword ? (
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              {passwordError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {passwordError}
                </div>
              )}

              <Input
                label="Nueva Contraseña"
                type="password"
                value={passwordData.newPassword}
                onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                required
                placeholder="Mínimo 6 caracteres"
              />

              <Input
                label="Confirmar Contraseña"
                type="password"
                value={passwordData.confirmPassword}
                onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                required
              />

              <div className="flex space-x-3 pt-4">
                <Button type="submit">Actualizar Contraseña</Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setIsChangingPassword(false);
                    setPasswordData({
                      currentPassword: '',
                      newPassword: '',
                      confirmPassword: '',
                    });
                    setPasswordError('');
                  }}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          ) : (
            <p className="text-gray-600">
              Haz clic en "Cambiar" para actualizar tu contraseña
            </p>
          )}
        </Card>

        {/* Roles and Permissions */}
        <Card title="Mis Roles y Permisos">
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Roles Asignados</h3>
              <div className="flex flex-wrap gap-2">
                {user.roles.length > 0 ? (
                  user.roles.map((role) => (
                    <span
                      key={role.id}
                      className="px-3 py-1 bg-purple-100 text-purple-800 text-sm rounded-lg font-medium"
                    >
                      🎭 {role.name}
                    </span>
                  ))
                ) : (
                  <p className="text-gray-500 text-sm">No tienes roles asignados</p>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Permisos ({user.roles.reduce((acc, role) => acc + role.permissions.length, 0)} totales)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {user.roles.map((role) => (
                  <div key={role.id} className="border border-gray-200 rounded-lg p-4">
                    <h4 className="font-medium text-gray-800 mb-2">{role.name}</h4>
                    <div className="space-y-1">
                      {role.permissions.map((perm) => (
                        <div key={perm.id} className="flex items-center space-x-2 text-sm">
                          <span className="text-green-600">✓</span>
                          <span className="text-gray-700">{perm.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
