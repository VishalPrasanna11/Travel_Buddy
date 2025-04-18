// import { Route, Routes, Navigate } from "react-router-dom"
// import Layout from "./layouts/layout"
// import HomePage from "./pages/HomePage"
// import AuthCallbackPage from "./pages/AuthCallbackPage"
// import ProtectedRoute from "./auth/ProtectedRoute"
// import ChatPage from "./pages/ChatPage"
// import ChatMapsPage from "./pages/ChatMapsPage"
// import LandingPage from "./pages/LandingPage"
// import ChatMainPage from "./pages/ChatMainPage"

// const AppRouter = () => {
//   return (
//     <Routes>
//       {/* Public Route - Landing */}
//       <Route
//         path="/"
//         element={
//           <Layout showFooter showSidebar={false}>
//             <LandingPage />
//           </Layout>
//         }
//       />

//       {/* Public Route - Auth Callback */}
//       <Route path="/auth-callback" element={<AuthCallbackPage />} />

//       {/* Protected Routes */}
//       <Route element={<ProtectedRoute />}>
        
        
//         <Route 
//           path="/chat/:id"
//           element={
//             <Layout showHero={false} showSidebar>
//               <ChatMainPage />
//             </Layout>
//           } 
//         />
        
//         <Route 
//           path="/home" 
//           element={
//             <Layout showHero showFooter>
//               <HomePage />
//             </Layout>
//           } 
//         />
        
//         <Route
//           path="/chatmaps"
//           element={
//             <Layout showHero={false} showSidebar>
//               <ChatMapsPage />
//             </Layout>
//           }
//         />
//         <Route
//           path="/chatmain/:id"
//           element={
//             <Layout showHero={false} showSidebar>
//              <ChatMainPage />
//             </Layout>
//           }
//         />
//       </Route>

//       {/* Catch-all redirect */}
//       <Route path="*" element={<Navigate to="/" replace />} />
//     </Routes>
//   )
// }

// export default AppRouter




import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import ChatMapsPage from './pages/ChatMapsPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import LandingPage from './pages/LandingPage';
import FlightSearchPage from './pages/FlightSearchPage'; // Add this import

const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/chat" element={<ChatPage />} />
      <Route path="/maps" element={<ChatMapsPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/flights" element={<FlightSearchPage />} /> {/* Add this route */}
    </Routes>
  );
};

export default AppRouter;