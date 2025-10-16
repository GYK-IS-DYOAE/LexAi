import { createBrowserRouter } from "react-router-dom";

import PublicLayout from "@/components/layout/PublicLayout";
import PrivateLayout from "@/components/layout/PrivateLayout";
import ProtectedRoute from "@/components/ProtectedRoute";

import LandingPage from "@/features/landing/LandingPage";
import Login from "@/features/auth/Login";
import Register from "@/features/auth/Register";
import HomePage from "@/features/home/HomePage";
import ChatPage from "@/features/chat/ChatPage";
import SimilarCasesPage from "@/features/similar/SimilarCasesPage";

import AdminDashboard from "@/features/admin/AdminDashboard";
import UserList from "@/features/admin/UserList";
import FeedbackList from "@/features/admin/FeedbackList";

export const router = createBrowserRouter([

  {
    element: <PublicLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: "/login", element: <Login /> },
      { path: "/register", element: <Register /> },
    ],
  },

  {
    element: (
      <ProtectedRoute>
        <PrivateLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: "/home", element: <HomePage /> },
      { path: "/chat", element: <ChatPage /> },
      { path: "/similar", element: <SimilarCasesPage /> },

      //Admin routes
      {
        path: "/admin",
        element: (
          <ProtectedRoute requiredAdmin>
            <AdminDashboard />
          </ProtectedRoute>
        ),
      },
      {
        path: "/admin/users",
        element: (
          <ProtectedRoute requiredAdmin>
            <UserList />
          </ProtectedRoute>
        ),
      },
      {
        path: "/admin/feedbacks",
        element: (
          <ProtectedRoute requiredAdmin>
            <FeedbackList />
          </ProtectedRoute>
        ),
      },
    ],
  },
]);
