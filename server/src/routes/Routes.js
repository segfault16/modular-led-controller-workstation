import { Home, ContentPaste, Notifications, AccountCircle } from '@material-ui/icons';
import EditProjectPage from '../pages/EditProjectPage';


const Routes = [
  {
    path: '/dashboard/home',
    sidebarName: 'Home',
    navbarName: 'Home',
    icon: Home,
    component: EditProjectPage
  }
];

export default Routes;