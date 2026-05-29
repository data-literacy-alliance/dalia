import React, { cloneElement, FC, ReactElement } from 'react';
import { HFlex } from '@/components/Flex';
import Button, { ButtonProps } from '@/components/Button/Button';

const ButtonGroup: FC<ButtonGroupProps> = ({
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

export type ButtonGroupProps = {
  children: ReactElement<ButtonProps & { value: string }, typeof Button>[];
  value: string;
  onChange?: (newValue: string) => void;
  className?: string;
};

export default ButtonGroup;
