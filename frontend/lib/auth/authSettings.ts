export const AUTH_ACCESS_KEY = 'access';
export const AUTH_REFRESH_KEY = 'refresh';

export type UserInfo = {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_curator: boolean;
  groups: {
    id: number;
    name: string;
  }[];
  user_permissions: string[];
  effective_permissions: string[];
};
