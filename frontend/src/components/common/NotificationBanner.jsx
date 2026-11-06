import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { clearNotification } from '../../store/uiSlice';
import Toast from '../ui/Toast';

export const NotificationBanner = () => {
  const dispatch = useDispatch();
  const notification = useSelector((state) => state.ui.notification);

  if (!notification) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 max-w-sm w-full animate-fade-in">
      <Toast
        type={notification.type}
        message={notification.message}
        onDismiss={() => dispatch(clearNotification())}
        duration={4000}
      />
    </div>
  );
};

export default NotificationBanner;
