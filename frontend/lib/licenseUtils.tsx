import { ReactNode } from 'react';
import { BASE_PATH } from '@/lib/settings.mjs';
import Image from 'next/image';

const numbersRegex = /\d\.\d/;

export function getLicenseIcons(license: string): ReactNode {
  if (!license.startsWith('CC')) {
    return license;
  }

  let parts = license.split('-');
  const versionIndex = parts.findIndex((part) => numbersRegex.test(part));

  if (versionIndex > 0) {
    parts = parts.slice(0, versionIndex);
  }

  return (
    <span className={'inline-flex flex-nowrap gap-1'}>
      {parts.map((part) =>
        part in licenseToImage ? (
          <Image
            src={licenseToImage[part]}
            key={part}
            alt={part}
            width={25}
            height={25}
            title={part}
          />
        ) : (
          part
        )
      )}
    </span>
  );
}

const licenseToImage: Record<string, string> = {
  CC0: `${BASE_PATH}/images/licenses/Zero.png`,
  CC: `${BASE_PATH}/images/licenses/CC.png`,
  BY: `${BASE_PATH}/images/licenses/BY.png`,
  NC: `${BASE_PATH}/images/licenses/NC.png`,
  ND: `${BASE_PATH}/images/licenses/ND.png`,
  SA: `${BASE_PATH}/images/licenses/SA.png`,
};
