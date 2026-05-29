import React from 'react';
import { HFlex, VFlex } from '@/components/Flex';
import styles from '@/app/(blueBg)/forgot-password/forgot_password.module.css';
import TopBar from '@/app/_parts/TopBar';
import { BASE_PATH } from '@/lib/settings.mjs';

export default function ResetPasswordBody() {
  return (
    <VFlex
      className={styles.mainBody}
      style={{
        backgroundImage: `url(${BASE_PATH}/images/search-bg.svg)`,
      }}
    >
      <TopBar activePage={'resetPassword'} />
      <HFlex className="h-full items-center justify-center">
        <div className={'max-w-96 bg-daliaGray-100 p-10'}>
          The login functionality is disabled for now. We will launch a larger
          package with user functionality in our next milestone. Stay tuned!
          {/*<VFlex>*/}
          {/*  <Text className={'mb-5 self-center'} variant={'h4'}>*/}
          {/*    Reset Password*/}
          {/*  </Text>*/}
          {/*  <Text className={'mb-5 self-start text-justify'}>*/}
          {/*    Enter a new password*/}
          {/*  </Text>*/}
          {/*  <TextBox*/}
          {/*    inputClassname={'py-2 min-w-72 mb-5'}*/}
          {/*    label={'Password'}*/}
          {/*  ></TextBox>*/}
          {/*  <TextBox*/}
          {/*    inputClassname={'py-2 min-w-72 mb-5'}*/}
          {/*    label={'Re-enter Password'}*/}
          {/*  ></TextBox>*/}
          {/*  <Button*/}
          {/*    className={'mb-5'}*/}
          {/*    small={false}*/}
          {/*    dark={true}*/}
          {/*    trailIcon={'arrow-right'}*/}
          {/*  >*/}
          {/*    Submit*/}
          {/*  </Button>*/}
          {/*</VFlex>*/}
        </div>
      </HFlex>
    </VFlex>
  );
}
