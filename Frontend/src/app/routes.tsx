import { createBrowserRouter, RouteObject } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const Home = lazy(() => import('@/pages/home/Home'));
const NotFound = lazy(() => import('@/pages/errors/NotFound'));
const Players = lazy(() => import('@/pages/players/Players'));
const Settings = lazy(() => import('@/pages/settings/Settings'));
const Server = lazy(() => import('@/pages/server/Server'));
const Map = lazy(() => import('@/pages/map/Map'));
const Login = lazy(() => import('@/pages/auth/Login'));
const ChangePassword = lazy(() => import('@/pages/auth/ChangePassword'));
const ActivateDiscord = lazy(() => import('@/pages/auth/ActivateDiscord'));
const Tools = lazy(() => import('@/pages/tools/Tools'));
const ToolRouter = lazy(() => import('@/pages/tools/ToolRouter'));
const Unauthorized = lazy(() => import('@/pages/errors/Unauthorized'));
const ShopDeliveriesTransactions = lazy(() => import('@/pages/tools/ShopDeliveriesTransactions'));
const ScheduledNotifications = lazy(() => import('@/pages/server/ScheduledNotifications'));

const routes: RouteObject[] = [
  // Rotas públicas (autenticação)
  {
    path: '/login',
    element: (
      <Suspense>
        <Login />
      </Suspense>
    ),
  },
  {
    path: '/change-password',
    element: (
      <Suspense>
        <ChangePassword />
      </Suspense>
    ),
  },
  {
    path: '/activate-discord',
    element: (
      <Suspense>
        <ActivateDiscord />
      </Suspense>
    ),
  },
  {
    path: '/unauthorized',
    element: (
      <Suspense>
        <Unauthorized />
      </Suspense>
    ),
  },
  // Rotas protegidas
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <Suspense>
            <Home />
          </Suspense>
        ),
      },
      {
        path: 'players',
        element: (
          <Suspense>
            <Players />
          </Suspense>
        ),
      },
      {
        path: 'tools',
        element: (
          <ProtectedRoute requireAdmin>
            <Suspense>
              <Tools />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'tools/:tool',
        element: (
          <ProtectedRoute requireAdmin>
            <Suspense>
              <ToolRouter />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'tools/shop-deliveries/transactions/:steamId',
        element: (
          <ProtectedRoute requireAdmin>
            <Suspense>
              <ShopDeliveriesTransactions />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'settings',
        element: (
          <Suspense>
            <Settings />
          </Suspense>
        ),
      },
      {
        path: 'server',
        element: (
          <Suspense>
            <Server />
          </Suspense>
        ),
      },
      {
        path: 'server/notifications/scheduled',
        element: (
          <ProtectedRoute requireAdmin>
            <Suspense>
              <ScheduledNotifications />
            </Suspense>
          </ProtectedRoute>
        ),
      },
      {
        path: 'map',
        element: (
          <Suspense>
            <Map />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '*',
    element: (
      <Suspense>
        <NotFound />
      </Suspense>
    ),
  },
];

export const router = createBrowserRouter(routes);


