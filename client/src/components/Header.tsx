import { Link } from "react-router-dom";
import MainNav from "./MainNav";
import MobileNav from "./MobileNav";

const Header = () => {
    return (
        <header className="border-b-2 border-b-black py-4">
            <div className="container mx-auto flex justify-between items-center">
                <Link to="/" className="text-#0A0A0A  text-3xl tracking-tight font-bold">TravelBuddy</Link>
                <div className="md:hidden">
                    <MobileNav/>
                </div>
                <div className="hidden md:block">

                   
                    <MainNav/>
                </div>
            </div>
        </header>
    );
}
export default Header;