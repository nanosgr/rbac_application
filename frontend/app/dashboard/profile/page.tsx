'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { userService } from '@/lib/api/services';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Card from '@/components/common/Card';
import Input from '@/components/common/Input';
import Button from '@/components/common/Button';
import { UpdateProfileDTO, ChangePasswordDTO } from '@/types';
import { Pencil, Save, X, Lock, ShieldCheck } from 'lucide-react';

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const { success } = useToast();

  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileData, setProfileData] = useState<UpdateProfileDTO>({
    full_name: user?.full_name ?? '',
    email: user?.email ?? '',
  });
  const [profileError, setProfileError] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const [passwordData, setPasswordData] = useState<ChangePasswordDTO & { confirm: string }>({
    current_password: '',
    new_password: '',
    confirm: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const [isSavingPwd, setIsSavingPwd] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileData({ full_name: user.full_name, email: user.email });
    }
  }, [user]);

  if (!user) {
    return <DashboardLayout title="Mi Perfil"><Card><p>Cargando...</p></Card></DashboardLayout>;
  }

  const handleProfileSubmit = async () => {
    setProfileError('');
    if (!profileData.email) { setProfileError('El email es obligatorio'); return; }
    setIsSavingProfile(true);
    try {
      const updatedUser = await userService.updateMe(profileData);
      setUser(updatedUser);
      setIsEditingProfile(false);
      success('Perfil actualizado correctamente');
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : 'Error al actualizar el perfil');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handlePasswordSubmit = async () => {
    setPasswordError('');
    if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm) {
      setPasswordError('Todos los campos son obligatorios');
      return;
    }
    if (passwordData.new_password !== passwordData.confirm) {
      setPasswordError('Las contraseñas nuevas no coinciden');
      return;
    }
    if (passwordData.new_password.length < 8) {
      setPasswordError('La nueva contraseña debe tener al menos 8 caracteres');
      return;
    }
    setIsSavingPwd(true);
    try {
      await userService.changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });
      setPasswordData({ current_password: '', new_password: '', confirm: '' });
      success('Contraseña actualizada correctamente');
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Error al cambiar la contraseña');
    } finally {
      setIsSavingPwd(false);
    }
  };

  const cancelEdit = () => {
    setIsEditingProfile(false);
    setProfileData({ full_name: user.full_name, email: user.email });
    setProfileError('');
  };

  return (
    <DashboardLayout title="Mi Perfil">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Información Personal */}
        <Card
          title="Información Personal"
          actions={
            !isEditingProfile ? (
              <Button variant="secondary" size="sm" onClick={() => setIsEditingProfile(true)} className="flex items-center gap-2">
                <Pencil className="w-4 h-4" />
                Editar
              </Button>
            ) : undefined
          }
        >
          {/* Avatar + resumen */}
          <div className="flex items-center space-x-6 mb-6 pb-6 border-b border-gray-100">
            <div className="w-20 h-20 rounded-full bg-blue-500 flex items-center justify-center text-white text-3xl font-bold flex-shrink-0">
              {user.username[0].toUpperCase()}
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">{user.full_name || user.username}</h3>
              <p className="text-gray-500 text-sm">@{user.username}</p>
              <div className="flex gap-2 mt-2 flex-wrap">
                {user.is_superuser && (
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" /> Superusuario
                  </span>
                )}
                {user.roles.map((r) => (
                  <span key={r.id} className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded-full">
                    {r.name}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {isEditingProfile ? (
            <div className="space-y-4">
              {profileError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{profileError}</div>
              )}
              <Input
                label="Nombre Completo"
                value={profileData.full_name ?? ''}
                onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
              />
              <Input
                label="Email *"
                type="email"
                value={profileData.email ?? ''}
                onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
              />
              <div className="flex gap-3 pt-2">
                <Button onClick={handleProfileSubmit} disabled={isSavingProfile} className="flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  {isSavingProfile ? 'Guardando...' : 'Guardar'}
                </Button>
                <Button variant="secondary" onClick={cancelEdit} className="flex items-center gap-2">
                  <X className="w-4 h-4" />
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Usuario</p>
                <p className="mt-1 text-gray-900">{user.username}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Nombre Completo</p>
                <p className="mt-1 text-gray-900">{user.full_name || '—'}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Email</p>
                <p className="mt-1 text-gray-900">{user.email}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Estado</p>
                <span className={`mt-1 inline-block px-2 py-1 text-xs font-medium rounded-full ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {user.is_active ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Miembro desde</p>
                <p className="mt-1 text-gray-900">
                  {user.created_at ? new Date(user.created_at).toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' }) : '—'}
                </p>
              </div>
            </div>
          )}
        </Card>

        {/* Cambiar Contraseña */}
        <Card title="Cambiar Contraseña">
          <div className="flex items-center gap-2 mb-5 text-gray-500">
            <Lock className="w-4 h-4" />
            <span className="text-sm">Debes ingresar tu contraseña actual para confirmar el cambio.</span>
          </div>
          <div className="space-y-4 max-w-md">
            <Input
              label="Contraseña actual"
              type="password"
              value={passwordData.current_password}
              onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })}
              placeholder="Tu contraseña actual"
            />
            <Input
              label="Nueva contraseña"
              type="password"
              value={passwordData.new_password}
              onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
              placeholder="Mínimo 8 caracteres"
            />
            <Input
              label="Confirmar nueva contraseña"
              type="password"
              value={passwordData.confirm}
              onChange={(e) => setPasswordData({ ...passwordData, confirm: e.target.value })}
              placeholder="Repite la nueva contraseña"
            />
            {passwordError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{passwordError}</div>
            )}
            <Button onClick={handlePasswordSubmit} disabled={isSavingPwd} className="flex items-center gap-2">
              <Save className="w-4 h-4" />
              {isSavingPwd ? 'Cambiando...' : 'Cambiar Contraseña'}
            </Button>
          </div>
        </Card>

        {/* Roles y Permisos */}
        <Card title="Mis Roles y Permisos">
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Roles Asignados</h3>
              <div className="flex flex-wrap gap-2">
                {user.roles.length > 0 ? (
                  user.roles.map((role) => (
                    <span key={role.id} className="px-3 py-1 bg-purple-100 text-purple-800 text-sm rounded-lg font-medium">
                      {role.name}
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
                          <span className="text-green-600 font-bold">✓</span>
                          <span className="text-gray-700 font-mono text-xs">{perm.name}</span>
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
