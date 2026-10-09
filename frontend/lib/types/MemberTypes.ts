export type MemberRole =
  | 'ADMINISTRATOR'
  | 'MODERATORS'
  | 'LECTURERS'
  | 'LEARNERS';

export type MembersObject = {
  id: number;
  thumbnail: string;
  name: string;
  about: string;
  institute: string;
  role: MemberRole;
  tags: string[];
};
