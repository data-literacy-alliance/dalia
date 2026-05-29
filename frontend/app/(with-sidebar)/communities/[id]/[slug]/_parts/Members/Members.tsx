import React, { Suspense } from 'react';
import { HFlex, VFlex } from '../../../../../../../components/Flex';
import styles from './Members.module.css';
import Text from '../../../../../../../components/Text';
import { dummyMembers } from '@/lib/dummy';
import Collapsible from '@/components/Collapsible';
import MemberCard from '@/components/MemberCard';
import Pages from '@/app/_parts/Pages';

const Members = () => {
  return (
    <VFlex className={styles.body}>
      <Text variant={'h4'} className={styles.memberCollapsible}>
        {dummyMembers.length} Total Members
      </Text>
      <Collapsible
        className={styles.memberCollapsible}
        defaultOpen={true}
        title={
          <Text variant={'subheader'} className={styles.collapsibleTitle}>
            ADMINISTRATOR
          </Text>
        }
      >
        <HFlex className={styles.memberGrid}>
          {dummyMembers
            .filter((member) => member.role === 'ADMINISTRATOR')
            .map((member) => (
              <MemberCard member={member} key={member.id} />
            ))}
        </HFlex>
      </Collapsible>
      <Collapsible
        className={styles.memberCollapsible}
        defaultOpen={true}
        title={
          <Text variant={'subheader'} className={styles.collapsibleTitle}>
            MODERATORS
          </Text>
        }
      >
        <HFlex className={styles.memberGrid}>
          {dummyMembers
            .filter((member) => member.role === 'MODERATORS')
            .map((member) => (
              <MemberCard member={member} key={member.id} />
            ))}
        </HFlex>
      </Collapsible>
      <Collapsible
        className={styles.memberCollapsible}
        defaultOpen={true}
        title={
          <Text variant={'subheader'} className={styles.collapsibleTitle}>
            LECTURERS
          </Text>
        }
      >
        <HFlex className={styles.memberGrid}>
          {dummyMembers
            .filter((member) => member.role === 'LECTURERS')
            .map((member) => (
              <MemberCard member={member} key={member.id} />
            ))}
        </HFlex>
      </Collapsible>
      <Collapsible
        className={styles.memberCollapsible}
        defaultOpen={true}
        title={
          <Text variant={'subheader'} className={styles.collapsibleTitle}>
            LEARNERS
          </Text>
        }
      >
        <HFlex className={styles.memberGrid}>
          {dummyMembers
            .filter((member) => member.role === 'LEARNERS')
            .map((member) => (
              <MemberCard member={member} key={member.id} />
            ))}
        </HFlex>
      </Collapsible>
      <Suspense>
        <Pages limit={20} count={20} offset={0} />
      </Suspense>
    </VFlex>
  );
};

export default Members;
