import { Route, Routes } from "react-router-dom"
import Layout from "./layouts/layout" // Import the 'Layout' component
import HomePage from "./pages/HomePage"
import AutHCallbackPage from "./pages/AuthCallbackPage";
import ProtectedRoute from "./auth/ProtectedRoute";
import { ChatPage } from "./pages/ChatPage";
import LandingPage from "./pages/LandingPage";


const AppRouter = () => {
    return(
        <Routes>
            <Route path="/" element={
            <Layout showFooter showSidebar={false}>
                <LandingPage/>
            </Layout>} />
            
            
            
            <Route path="/auth-callback" element={
                <AutHCallbackPage/>
            } />

           
           
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
           
            } /> */}
            </Route>
            
        </Routes>
    )}
export default AppRouter;