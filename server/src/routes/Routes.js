import { Home, ContentPaste, Notifications, AccountCircle } from '@material-ui/icons';
import EditProjectPage from '../pages/EditProjectPage';


const Routes = [
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
    component: EditProjectPage
  }
];

export default Routes;