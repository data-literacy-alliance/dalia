'use client';
import React, { FC, useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import Text, { TextProps } from '@/components/Text';

const DescriptionPart: FC<DescriptionPartProps> = (props) => {
  const [descriptionHeight, setDescriptionHeight] = useState<number | null>(
    null
  );
  const [isExpanded, setIsExpanded] = useState(false);
  const [needsTruncation, setNeedsTruncation] = useState(false);
  const [maxHeight, setMaxHeight] = useState<string | undefined>(undefined);
  const textRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const checkOverflow = () => {
      if (textRef.current && descriptionHeight) {
        const lineHeight = parseFloat(
          getComputedStyle(textRef.current).lineHeight
        );
        setNeedsTruncation(textRef.current.scrollHeight > descriptionHeight);

        if (!isExpanded) {
          // subtract a line and 2 x padding for 'show more' button.
          setMaxHeight(
            `${textRef.current.scrollHeight > descriptionHeight ? descriptionHeight - lineHeight - 32 : descriptionHeight}px`
          );
        } else {
          setMaxHeight(`${textRef.current.scrollHeight}px`);
        }
      }
    };

    if (window) {
      checkOverflow();

      // Recalculate when window resizes
      window.addEventListener('resize', checkOverflow);
      return () => window.removeEventListener('resize', checkOverflow);
    }
  }, [isExpanded, descriptionHeight]);

  const toggleExpand = () => {
    if (textRef.current) {
      setMaxHeight(
        isExpanded
          ? `${textRef.current.scrollHeight}px`
          : `${needsTruncation ? descriptionHeight! - parseFloat(getComputedStyle(textRef.current).lineHeight) : descriptionHeight}px`
      );
    }
    setIsExpanded((prev) => !prev);
  };

  return (
    <div
      className={cn(
        'border-b border-primary px-6 py-4 max-lg:hidden xl:px-16',
        {
          'h-full': descriptionHeight === null,
        }
      )}
      style={
        !needsTruncation && descriptionHeight
          ? {
              height: descriptionHeight + 1,
            }
          : undefined
      }
      ref={(ref) => {
        // only measure once
        if (ref && descriptionHeight === null) {
          setDescriptionHeight(ref.clientHeight);
        }
      }}
    >
      {descriptionHeight !== null && (
        <>
          <Text
            {...props}
            className={cn(
              'block overflow-hidden transition-all duration-500 ease-in-out',
              {
                'h-full': !needsTruncation,
              },
              props.className
            )}
            property={'dcterms:description'}
            style={{ maxHeight }}
            ref={textRef}
          />
          {needsTruncation && (
            <Text onClick={toggleExpand} className={'cursor-pointer underline'}>
              {isExpanded ? 'Show less...' : 'Show more...'}
            </Text>
          )}
        </>
      )}
    </div>
  );
};

export type DescriptionPartProps = Omit<TextProps, 'ref'>;

export default DescriptionPart;
