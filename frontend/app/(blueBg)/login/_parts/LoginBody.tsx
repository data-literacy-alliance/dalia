import React from 'react';
import { VFlex } from '@/components/Flex';
import Text from '@/components/Text';
import Button from '@/components/Button';

export default function LoginBody() {
  return (
    <div className={'mt-10 bg-daliaGray-100 p-10'}>
      <VFlex>
        <Text className={'mb-10 self-center'} variant={'h4'}>
          Log in
        </Text>
        <Button
          className={'w-full'}
          dark={true}
          small={false}
          trailIcon={'arrow-right'}
          link={{ href: '/accounts/oidc/iam4nfdi/login/?process=login' }}
        >
          Login with IAM4NFDI
        </Button>
      </VFlex>
    </div>
  );
}
