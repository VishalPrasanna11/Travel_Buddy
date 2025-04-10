import hero from '../assets/hero.png';

const Hero = () => {
    return (
        <div className="hero">
            <img src={hero} alt="hero" className="w-full max-h-[800px] object-cover" />
            
        </div>
    );
};

export default Hero;