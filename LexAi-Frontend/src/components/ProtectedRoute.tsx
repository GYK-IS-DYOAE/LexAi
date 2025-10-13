import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/features/auth/useAuthStore";

interface Props {
  children: React.ReactNode;
  requiredAdmin?: boolean;
}

export default function ProtectedRoute({ children, requiredAdmin }: Props) {
  const { user, token } = useAuthStore();

  if (!token) {
    return <Navigate to="/auth/login" replace />;
  }

  if (requiredAdmin && !user?.is_admin) {
    return <Navigate to="/home" replace />;
  }

  return <>{children}</>;
}
