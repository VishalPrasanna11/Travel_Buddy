import { Route, Routes } from "react-router-dom"
import Layout from "./layouts/layout" // Import the 'Layout' component
import HomePage from "./pages/HomePage"
import AutHCallbackPage from "./pages/AuthCallbackPage";
import ProtectedRoute from "./auth/ProtectedRoute";
import { ChatPage } from "./pages/ChatPage";


const AppRouter = () => {
    return(
        <Routes>
            <Route path="/" element={
            <Layout showHero showFooter>
                <HomePage/>
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
                 <Route path="/chat"
                 element = {
                 <Layout showHero={false}>
                    <ChatPage/>
                 </Layout>} />
            }
            {/* <Route path="/profile" element={
            <Layout>
                <UserProfilePage/>
            </Layout>
           
            } /> */}
            {/* <Route path="/restaurant" element={
            <Layout>
                <RestauarantPage/>
            </Layout>
           
            } /> */}
            </Route>
            
        </Routes>
    )}
export default AppRouter;