import React from 'react';

export const Skeleton = ({
  variant = 'text', // 'text' | 'rectangular' | 'circular'
  width,
  height,
  className = '',
}) => {
  const variants = {
    text: 'h-3.5 rounded-md',
    rectangular: 'rounded-xl',
    circular: 'rounded-full',
  };

  const style = {
    width: width ? (typeof width === 'number' ? `${width}px` : width) : undefined,
    height: height ? (typeof height === 'number' ? `${height}px` : height) : undefined,
  };

  return (
    <div
      style={style}
      className={`animate-pulse bg-slate-200/80 ${variants[variant] || variants.text} ${className}`}
      aria-hidden="true"
    />
  );
};

export default Skeleton;

