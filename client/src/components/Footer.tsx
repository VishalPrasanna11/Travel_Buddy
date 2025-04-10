const Footer = () => {
    return (
        <footer>
            <div className="bg-black py-8">
                <div className="container mx-auto flex flex-col md:flex-row justify-between items-center">
                    <span className="text-white text-3xl font-bold">TravelBuddy</span>
                    <span className="text-white font-bold tracking-tight flex gap-4">
                        <span>&copy; 2025 TravelBuddy</span>
                        <span>Privacy Policy</span>
                        <span>Terms of Service</span>
                    </span>
                </div>
            </div>
        </footer>
    );  
    }   
    export default Footer;