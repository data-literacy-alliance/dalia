import React from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import Icon from '@/components/Icon/Icon';
import Text from '@/components/Text/Text';
import Button from '@/components/Button/Button';
import Link from 'next/link';
import Image from 'next/image';
import FundedByEU from './funders/FundedByEU.png';
import BMFTR from './funders/BMFTR.jpg';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faBluesky,
  faMastodon,
  faYoutube,
} from '@fortawesome/free-brands-svg-icons';

import { faUsers } from '@fortawesome/free-solid-svg-icons';
import { StaticImport } from 'next/dist/shared/lib/get-img-props';
import {
  LoginURL,
  NEXT_PUBLIC_DALIA_NEWSLETTER_LINK,
  NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK,
} from '@/lib/settings.mjs';

const Footer = () => {
  return (
    <div className={'flex flex-col bg-white lg:flex-row'}>
      <div className={'border-primary lg:w-[30%] lg:border-e'}>
        <HFlex
          className={
            'h-52 items-center justify-center gap-4 border-t border-primary pb-12 pt-20'
          }
        >
          <Icon source={'logo'} size={79} />
          <Text className={'line- text-[1.375rem] leading-[120%] text-primary'}>
            Data
            <br />
            Literacy
            <br />
            Alliance
          </Text>
        </HFlex>
        <div className={'border-t border-primary px-5 py-20'}>
          <VFlex className={'gap-12'}>
            <Text variant={'h4'}>Sign up to our newsletter</Text>
            <Text>
              The DALIA newsletter informs you about upcoming events and
              milestones.
            </Text>
            <VFlex className={'gap-5'}>
              <Button
                dark
                className={'w-full'}
                link={{
                  href: NEXT_PUBLIC_DALIA_NEWSLETTER_SUBSCRIBE_LINK,
                  target: '_blank',
                }}
              >
                Subscribe to Newsletter
              </Button>
              <Button
                dark
                className={'w-full'}
                link={{
                  href: NEXT_PUBLIC_DALIA_NEWSLETTER_LINK,
                  target: '_blank',
                }}
              >
                View Newsletter
              </Button>
              {/*<HFlex className={'gap-5'}>*/}
              {/*  <Button dark className={'flex-1'}>*/}
              {/*    Unsubscribe*/}
              {/*  </Button>*/}
              {/*  <Button dark className={'flex-1'}>*/}
              {/*    Archive*/}
              {/*  </Button>*/}
              {/*</HFlex>*/}
            </VFlex>
          </VFlex>
        </div>
        <VFlex
          className={
            'gap-8 border-t border-primary px-5 pb-12 pt-16 lg:px-24 lg:pt-24'
          }
        >
          <Text variant={'footerTitle'}>Follow</Text>
          <HFlex className={'gap-4'}>
            <a href="https://nfdi.social/@dalia" target={'_blank'}>
              <FontAwesomeIcon icon={faMastodon} className={'text-4xl'} />
            </a>
            <a
              href="https://www.youtube.com/@DALIA-edu/playlists"
              target={'_blank'}
            >
              <FontAwesomeIcon icon={faYoutube} className={'text-4xl'} />
            </a>
            <a href="https://zenodo.org/communities/dalia/" target={'_blank'}>
              <FontAwesomeIcon icon={faUsers} className={'text-3xl'} />
            </a>
            <a
              href="https://bsky.app/profile/daliaeducation.bsky.social"
              target={'_blank'}
            >
              <FontAwesomeIcon icon={faBluesky} className={'text-3xl'} />
            </a>
          </HFlex>
        </VFlex>
      </div>
      <div className={'flex-grow'}>
        <div className={'border-t border-primary lg:h-52'}></div>
        <VFlex
          className={
            'justify-around gap-3 border-primary px-5 py-16 md:flex-row lg:border-t lg:px-24'
          }
        >
          <VFlex className={'gap-6 lg:gap-12'}>
            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Search Portal</Text>
              <Link href={'/'} className={'hover:underline'}>
                <Text variant={'footerText'}>Basic Search</Text>
              </Link>
              <Link className={'hover:underline'} href={'/advanced'}>
                <Text variant={'footerText'}>Advanced Search</Text>
              </Link>
            </VFlex>

            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Account</Text>
              <Link
                href={LoginURL}
                target={'_blank'}
                className={'hover:underline'}
              >
                <Text variant={'footerText'}>Login</Text>
              </Link>
            </VFlex>
          </VFlex>

          <VFlex className={'gap-6 lg:gap-12'}>
            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Project Website</Text>
              <Link
                href={'https://dalia.education/en'}
                target={'_blank'}
                className={'hover:underline'}
              >
                <Text variant={'footerText'}>Home</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={
                  'https://dalia.education/en/arbeitsfelder/qualit%C3%A4tssicherung'
                }
              >
                <Text variant={'footerText'}>
                  Quality Control and Continuation
                </Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={'https://dalia.education/en/arbeitsfelder/kommunikation'}
              >
                <Text variant={'footerText'}>Communication</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={
                  'https://dalia.education/en/arbeitsfelder/informationsmodell'
                }
              >
                <Text variant={'footerText'}>Information Model</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={'https://dalia.education/en/arbeitsfelder/infrastruktur'}
              >
                <Text variant={'footerText'}>Infrastructure</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={
                  'https://dalia.education/en/arbeitsfelder/such-und_empfehlungsdienst'
                }
              >
                <Text variant={'footerText'}>
                  Search and Recommendation Engine
                </Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={'https://dalia.education/en#partners-and-funders'}
              >
                <Text variant={'footerText'}>Partners and Funders</Text>
              </Link>
            </VFlex>

            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Communities</Text>
              <Link href={'/communities'} className={'hover:underline'}>
                <Text variant={'footerText'}>View All Communities</Text>
              </Link>
              {/* Hidden for now - keep for potential future usage */}
              {/* <Link
                href={'/communities/guidelines'}
                className={'hover:underline'}
              >
                <Text variant={'footerText'}>Community Guidelines</Text>
              </Link> */}
            </VFlex>
          </VFlex>

          <VFlex className={'gap-6 lg:gap-12'}>
            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Legal</Text>
              <Link
                href={'/en/imprint'}
                target={'_blank'}
                className={'hover:underline'}
              >
                <Text variant={'footerText'}>Imprint</Text>
              </Link>
              <Link
                href={'/en/privacy-policy'}
                target={'_blank'}
                className={'hover:underline'}
              >
                <Text variant={'footerText'}>Privacy Policy</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={'/en/accessibility'}
              >
                <Text variant={'footerText'}>Declaration on Accessibility</Text>
              </Link>
              <Link
                className={'hover:underline'}
                target={'_blank'}
                href={'/en/terms'}
              >
                <Text variant={'footerText'}>Terms of Use</Text>
              </Link>
            </VFlex>

            <VFlex className={'items-center gap-2 lg:items-start lg:gap-7'}>
              <Text variant={'footerTitle'}>Funders</Text>
              <Link href={'https://commission.europa.eu/'} target={'_blank'}>
                <Image src={FundedByEU} alt={'Funded by EU'} width={180} />
              </Link>
              <Link href={'https://www.bmbf.de/'} target={'_blank'}>
                <Image
                  src={BMFTR as StaticImport}
                  alt={'BMFTR Logo'}
                  width={180}
                />
              </Link>
            </VFlex>
          </VFlex>
        </VFlex>
      </div>
    </div>
  );
};

export default Footer;
