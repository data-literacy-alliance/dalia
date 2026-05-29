import React, { FC } from 'react';
import styles from './Alert.module.css';

const Alert: FC<AlertProps> = ({ children }) => {
  return <div className={styles.root}>{children}</div>;
};

type AlertProps = {
  children: React.ReactNode;
};

export default Alert;
