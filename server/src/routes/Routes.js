import React from "react";
import { Redirect } from 'react-router';
import { Home, PlayArrow, Settings, Bookmarks } from '@material-ui/icons';
import EditProjectPage from '../pages/EditProjectPage';
import PerformPage from '../pages/PerformPage';
import ConfigurationPage from '../pages/ConfigurationPage';
import ProjectsPage from '../pages/ProjectsPage';

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
    path: '/dashboard/projects',
    sidebarName: 'Projects',
    navbarName: 'Projects',
    icon: Bookmarks,
    component: ProjectsPage
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