import React, { FC } from 'react';
import Button, { ButtonProps } from '@/components/Button/Button';
import {
  faBluesky,
  faFacebook,
  faInstagram,
  faLinkedin,
  faMastodon,
  faXTwitter,
  faYoutube,
} from '@fortawesome/free-brands-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { faUsers } from '@fortawesome/free-solid-svg-icons';

export const socialMediaIcons: Record<string, IconProp> = {
  facebook: faFacebook,
  linkedin: faLinkedin,
  instagram: faInstagram,
  youtube: faYoutube,
  x: faXTwitter,
  mastodon: faMastodon,
  zenodo: faUsers,
  bluesky: faBluesky,
};

const SocialMediaButton: FC<SocialMediaButtonProps> = ({
  socialMedia: origSocialMedia,
  ...props
}) => {
  const socialMedia = origSocialMedia.toLowerCase();

  return socialMedia in socialMediaIcons ? (
    <Button {...props}>
      <FontAwesomeIcon icon={socialMediaIcons[socialMedia]} />
      {origSocialMedia}
    </Button>
  ) : null;
};

export type SocialMediaButtonProps = ButtonProps & {
  socialMedia: string;
};

export default SocialMediaButton;
