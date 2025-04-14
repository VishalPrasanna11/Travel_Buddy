import { Route, Routes, Navigate } from "react-router-dom"
import Layout from "./layouts/layout"
import HomePage from "./pages/HomePage"
import AuthCallbackPage from "./pages/AuthCallbackPage"
import ProtectedRoute from "./auth/ProtectedRoute"
import ChatPage from "./pages/ChatPage"
import ChatMapsPage from "./pages/ChatMapsPage"
import LandingPage from "./pages/LandingPage"

const AppRouter = () => {
  return (
    <Routes>
      {/* Public Route - Landing */}
      <Route
        path="/"
        element={
          <Layout showFooter showSidebar={false}>
            <LandingPage />
          </Layout>
        }
      />


      {/* Public Route - Auth Callback */}
      <Route path="/auth-callback" element={<AuthCallbackPage />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route
          path="/chat"
          element={
            <Layout showHero={false} showSidebar>
              <ChatPage />

           
           
             {/* <Route path="/detail/:restaurantId"
             element = {
             <Layout showHero={false}>
                <DetailPage/>
             </Layout>} /> */}
            <Route element={<ProtectedRoute/>}>
            {
                 <Route path="/chat/:id"
                 element = {
                 <Layout showHero={false} showSidebar>
                    <ChatPage/>
                 </Layout>} />
                 
            }
            {
                <Route path="/home" element={
                    <Layout showHero showFooter>
                        <HomePage/>
                    </Layout>} />
            } 
            {/* <Route path="/restaurant" element={
            <Layout>
                <RestauarantPage/>

            </Layout>
          }
        />
        <Route
          path="/chatmaps"
          element={
            <Layout showHero={false} showSidebar>
              <ChatMapsPage />
            </Layout>
          }
        />
        <Route
          path="/home"
          element={
            <Layout showHero showFooter>
              <HomePage />
            </Layout>
          }
        />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRouter









// import { Route, Routes } from "react-router-dom"
// import Layout from "./layouts/layout" 
// import HomePage from "./pages/HomePage"
// import AutHCallbackPage from "./pages/AuthCallbackPage";
// import ProtectedRoute from "./auth/ProtectedRoute";
// import ChatPage from "./pages/ChatPage";
// import ChatMapsPage from "./pages/ChatMapsPage";
// import LandingPage from "./pages/LandingPage";
// import { Navigate } from "react-router-dom";

// const AppRouter = () => {
//     return(
//         <Routes>
//             <Route path="/" element={
//             <Layout showFooter showSidebar={false}>
//                 <LandingPage/>
//             </Layout>} />
            
//             <Route path="/auth-callback" element={
//                 <AutHCallbackPage/>
//             } />
           
//             <Route element={<ProtectedRoute/>}>
//                 <Route path="/chat"
//                 element = {
//                 <Layout showHero={false} showSidebar>
//                     <ChatPage/>
//                 </Layout>} />

//                 <Route element={<ProtectedRoute/>}>
//                 <Route path="/chatmaps"
//                 element = {
//                 <Layout showHero={false} showSidebar>
//                     <ChatMapsPage/>
//                 </Layout>} />

//                 </Route>
                
//                 <Route path="/home" element={
//                     <Layout showHero showFooter>
//                         <HomePage/>
//                     </Layout>} />

//                 {/* <Route path="/maps" element={
//                     <Layout showHero={false} showFooter>
//                         <Maps/>
//                     </Layout>} /> */}
//             </Route>
            
//         </Routes>
//     )}
// export default AppRouter;



