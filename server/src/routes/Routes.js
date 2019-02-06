import React from "react";
import { Redirect } from 'react-router';
import { Home, PlayArrow, Settings } from '@material-ui/icons';
import EditProjectPage from '../pages/EditProjectPage';
import PerformPage from '../pages/PerformPage';
import ConfigurationPage from '../pages/ConfigurationPage';

const Routes = [
  {
    path: '/',
    exact: true,
    component: () => <Redirect to="/dashboard/edit"/>
  },
  {
    path: '/dashboard/edit',
    sidebarName: 'Edit',
    navbarName: 'Edit',
    icon: Home,
    component: EditProjectPage
  },
  {
    path: '/dashboard/perform',
    sidebarName: 'Perform',
    navbarName: 'Perform',
    icon: PlayArrow,
    component: PerformPage
  },
  {
    path: '/dashboard/configuration',
    sidebarName: 'Configuration',
    navbarName: 'Configuration',
    icon: Settings,
    component: ConfigurationPage
  }
];

export default Routes;