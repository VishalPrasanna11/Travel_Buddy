import { Link } from "react-router-dom";
import { Instagram, Twitter, Facebook } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";  
 
const Footer = () => {
    return (
        <footer>
            <div className="bg-black py-8">
            {/* <div className="py-8" style={{ backgroundColor: "#374151" }}> */}
 
                <div className="container mx-auto px-4">
                    {/* Top section with logo and social */}
                    <div className="flex flex-col md:flex-row justify-between items-center mb-6">
                        
                         {/* Newsletter */}
      <div className="py-8 text-left space-y-6">
        <h2 className="text-3xl font-medium">Stay inspired</h2>
        <p className="text-muted-foreground max-w-md mx-auto">
          Subscribe to receive AI travel insights and personalized destination recommendations
        </p>
        <div className="flex max-w-md mx-auto">
          <Input placeholder="Your email address" className="rounded-r-none" />
          <Button className="rounded-l-none bg-raspberry hover:bg-raspberry/90">Subscribe</Button>
        </div>
      </div>
 
                        {/* Social media icons */}
                        <div className="flex gap-4 mt-4 md:mt-0">
                            <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" className="text-white hover:text-gray-300 transition-colors">
                                <Instagram size={20} />
                            </a>
                            <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="text-white hover:text-gray-300 transition-colors">
                                <Twitter size={20} />
                            </a>
                            <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" className="text-white hover:text-gray-300 transition-colors">
                                <Facebook size={20} />
                            </a>
                        </div>
                    </div>
                    
                    {/* Bottom section with links */}
                    <div className="flex flex-col md:flex-row justify-between items-center border-t border-gray-800 pt-6">
                        <span className="text-white text-sm">
                            &copy; {new Date().getFullYear()} TravelBuddy
                        </span>
                        
                        <div className="flex flex-wrap gap-6 mt-4 md:mt-0">
                            <Link to="/about" className="text-white text-sm hover:text-gray-300 transition-colors">
                                About
                            </Link>
                            <Link to="/contact" className="text-white text-sm hover:text-gray-300 transition-colors">
                                Contact
                            </Link>
                            <Link to="/privacy" className="text-white text-sm hover:text-gray-300 transition-colors">
                                Privacy Policy
                            </Link>
                            <Link to="/terms" className="text-white text-sm hover:text-gray-300 transition-colors">
                                Terms of Service
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </footer>
    );
}
 
export default Footer;