import React, { cloneElement, FC, ReactElement } from 'react';
import { HFlex } from '@/components/Flex';
import IconButton, {
  IconButtonProps,
} from '@/components/IconButton/IconButton';

const IconButtonGroup: FC<IconButtonGroupProps> = ({
  children,
  value,
  onChange,
  className,
}) => {
  const handleClick = (newValue: string) => () => {
    onChange?.(newValue);
  };

  return (
    <HFlex className={className}>
      {children.map((child) => {
        const childValue = child.props.value;

        return cloneElement(child, {
          className: child.props.className,
          dark: childValue === value,
          onClick: handleClick(childValue),
        });
      })}
    </HFlex>
  );
};

export type IconButtonGroupProps = {
  children: ReactElement<
    IconButtonProps & { value: string },
    typeof IconButton
  >[];
  value: string;
  onChange?: (newValue: string) => void;
  className?: string;
};

export default IconButtonGroup;
