import { SocialMediaField } from '@/lib/types/Common';

export type Community = {
  id: string;
  slug: string;
  title: string;
  image: string;
  url: string;
  social_media?: SocialMediaField[];
  about: string;
  likes: number;
  views: number;
  followers: number;
};
