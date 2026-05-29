import { HFlex, VFlex } from '@/components/Flex';
import styles from './MemberCard.module.css';
import Text from '@/components/Text';
import { MembersObject } from '@/lib/types/MemberTypes';
import Image from 'next/image';
import { FC } from 'react';

const MemberCard: FC<MemberCardProps> = ({ member }) => {
  return (
    <HFlex className={styles.container}>
      <div className={styles.thumbnail}>
        <Image
          src={member.thumbnail}
          alt="logo"
          fill={true}
          objectFit={'contain'}
        />
      </div>
      <VFlex className={'ml-5 justify-evenly'}>
        <VFlex>
          <Text className={'lg:text-xl'} variant={'subheader'}>
            {member.name}
          </Text>
          <Text className={'text-base'}>{member.institute}</Text>
        </VFlex>
        <HFlex className={styles.tags}>
          {member.tags.map((tag) => (
            <Text key={tag} className={'text-base'}>
              {tag}
            </Text>
          ))}
        </HFlex>
      </VFlex>
    </HFlex>
  );
};

export type MemberCardProps = {
  member: MembersObject;
};

export default MemberCard;
