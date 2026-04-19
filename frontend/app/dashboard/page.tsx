'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { userService, roleService, permissionService } from '@/lib/api/services';
import DashboardLayout from '@/components/layout/DashboardLayout';
import Card from '@/components/common/Card';
import { User } from '@/types';
import { Users, ShieldCheck, KeyRound, Star } from 'lucide-react';

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState({ totalUsers: 0, totalRoles: 0, totalPermissions: 0, activeUsers: 0 });
  const [recentUsers, setRecentUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        const [usersRes, rolesRes, permsRes, recentRes] = await Promise.all([
          userService.getAll({ page: 1, size: 1 }).catch(() => null),
          roleService.getAll({ page: 1, size: 1 }).catch(() => null),
          permissionService.getAll({ page: 1, size: 1 }).catch(() => null),
          userService.getAll({ page: 1, size: 5 }).catch(() => null),
        ]);

        const activeRes = await userService.getAll({ page: 1, size: 1, is_active: true }).catch(() => null);

        setStats({
          totalUsers: usersRes?.total ?? 0,
          totalRoles: rolesRes?.total ?? 0,
          totalPermissions: permsRes?.total ?? 0,
          activeUsers: activeRes?.total ?? 0,
        });
        setRecentUsers(recentRes?.items ?? []);
      } catch {
        // silencioso si no hay permisos
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  return (
    <DashboardLayout title="Panel de Control">
      <div className="space-y-6">
        {/* Welcome */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg shadow-lg p-6 text-white">
          <h2 className="text-2xl font-bold">Bienvenido, {user?.full_name}</h2>
          <p className="mt-2 text-blue-100">
            Panel de administración RBAC — {user?.roles?.[0]?.name ?? 'Usuario'}
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 font-medium">Total Usuarios</p>
                <p className="text-3xl font-bold text-gray-800 mt-2">
                  {isLoading ? '—' : stats.totalUsers}
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-green-600 font-medium">
              {stats.activeUsers} activos
            </div>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 font-medium">Roles</p>
                <p className="text-3xl font-bold text-gray-800 mt-2">
                  {isLoading ? '—' : stats.totalRoles}
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">Roles del sistema</div>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 font-medium">Permisos</p>
                <p className="text-3xl font-bold text-gray-800 mt-2">
                  {isLoading ? '—' : stats.totalPermissions}
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <KeyRound className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">Permisos configurados</div>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 font-medium">Mi Rol</p>
                <p className="text-lg font-bold text-gray-800 mt-2">
                  {user?.roles?.[0]?.name ?? 'N/A'}
                </p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <Star className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">
              {user?.is_superuser ? 'Acceso total' : 'Acceso limitado'}
            </div>
          </Card>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Usuarios Recientes">
            {isLoading ? (
              <div className="text-center py-8 text-gray-500">Cargando...</div>
            ) : recentUsers.length > 0 ? (
              <div className="space-y-3">
                {recentUsers.map((u) => (
                  <div
                    key={u.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-semibold">
                        {u.username[0].toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{u.full_name}</p>
                        <p className="text-sm text-gray-500">{u.email}</p>
                      </div>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {u.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">No hay usuarios registrados</div>
            )}
          </Card>

          <Card title="Mis Permisos">
            {user?.roles && user.roles.length > 0 ? (
              <div className="space-y-4">
                {user.roles.map((role) => (
                  <div key={role.id}>
                    <h4 className="font-semibold text-gray-800 mb-2">{role.name}</h4>
                    <div className="flex flex-wrap gap-2">
                      {role.permissions.slice(0, 6).map((perm) => (
                        <span
                          key={perm.id}
                          className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                        >
                          {perm.name}
                        </span>
                      ))}
                      {role.permissions.length > 6 && (
                        <span className="px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-full">
                          +{role.permissions.length - 6} más
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">No tienes roles asignados</div>
            )}
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
