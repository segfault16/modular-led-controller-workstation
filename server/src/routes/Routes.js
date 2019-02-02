import React from "react";
import { Redirect } from 'react-router';
import { Home, ContentPaste, Notifications, AccountCircle } from '@material-ui/icons';
import EditProjectPage from '../pages/EditProjectPage';
import PerformPage from '../pages/PerformPage';


const Routes = [
  {
    path: '/',
    exact: true,
    component: () => <Redirect to="/dashboard/configure"/>
  },
  {
    path: '/dashboard/configure',
    sidebarName: 'Configure',
    navbarName: 'Configure',
    icon: Home,
    component: EditProjectPage
  },
  {
    path: '/dashboard/perform',
    sidebarName: 'Perform',
    navbarName: 'Perform',
    icon: Home,
    component: PerformPage
  }
];

export default Routes;